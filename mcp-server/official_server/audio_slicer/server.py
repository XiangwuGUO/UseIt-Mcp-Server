"""
音频切片MCP服务器 - 标准化版本

基于节拍检测的音频文件切片服务，使用标准化MCP响应格式。

功能特性：
- 基于节拍的智能音频切片
- 支持多种音频格式（WAV, MP3, M4A, FLAC）
- 音频文件信息查询
- 服务状态监控
- 标准化响应格式确保兼容性

运行方式:
    python server.py
"""

import os
import base64
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from mcp.server.fastmcp import FastMCP

# 导入标准化组件
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from core import (
    MCPResponseBuilder, OperationType, create_file_info,
    ProcessingTool, quick_success, quick_error
)

# Import base directory manager
from base_dir_decorator import get_base_dir_manager

# 导入音频切片逻辑
from slicer import slice_audio_by_beats

# -----------------------------------------------------------------------------
# 服务器配置
# -----------------------------------------------------------------------------

SERVER_NAME = "audio_slicer"
SERVER_PORT = 8002

# 创建MCP服务器
mcp = FastMCP(
    name=SERVER_NAME,
    instructions="基于节拍检测的音频文件切片服务，使用标准化MCP响应格式"
)

# 创建处理工具实例
def get_base_dir():
    """获取基础工作目录"""
    base_dir_manager = get_base_dir_manager()
    return base_dir_manager.get_base_dir()

audio_tool = ProcessingTool("audio_slicer", get_base_dir())

# -----------------------------------------------------------------------------
# 音频处理工具
# -----------------------------------------------------------------------------

@mcp.tool()
def slice_audio_file(
    audio_file_content_base64: str,
    filename: str,
    segment_duration_s: float,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    基于节拍检测切分音频文件为多个片段
    
    Args:
        audio_file_content_base64: base64编码的音频文件内容
        filename: 原始音频文件名 (例如: 'track.mp3')
        segment_duration_s: 每个片段的目标时长（秒）
        session_id: 会话ID，用于工作空间隔离（可选）
    
    Returns:
        标准化的MCP响应，包含处理结果和生成的音频片段信息
    """
    builder = MCPResponseBuilder("slice_audio_file")
    
    try:
        # 验证输入参数
        if not audio_file_content_base64:
            return builder.error(
                operation=OperationType.PROCESS,
                message="音频数据不能为空",
                error_details="audio_file_content_base64 参数不能为空"
            ).to_dict()
        
        if segment_duration_s <= 0:
            return builder.error(
                operation=OperationType.PROCESS,
                message="片段时长必须大于0",
                error_details=f"segment_duration_s = {segment_duration_s} 无效"
            ).to_dict()
        
        # 使用临时目录处理音频
        with tempfile.TemporaryDirectory() as temp_dir:
            # 解码并保存音频文件
            try:
                audio_data = base64.b64decode(audio_file_content_base64)
            except Exception as e:
                return builder.error(
                    operation=OperationType.PROCESS,
                    message="音频数据解码失败",
                    error_details=f"base64解码错误: {str(e)}"
                ).to_dict()
            
            input_audio_path = os.path.join(temp_dir, filename)
            with open(input_audio_path, 'wb') as f:
                f.write(audio_data)
            
            # 设置输出目录
            processing_output_dir = os.path.join(temp_dir, "segments")
            
            # 调用音频切片逻辑
            try:
                segment_paths = slice_audio_by_beats(
                    audio_path=input_audio_path,
                    segment_duration_s=segment_duration_s,
                    output_dir=processing_output_dir
                )
            except Exception as e:
                return builder.error(
                    operation=OperationType.PROCESS,
                    message="音频切片处理失败",
                    error_details=f"切片算法错误: {str(e)}"
                ).to_dict()
            
            if not segment_paths:
                return builder.warning(
                    operation=OperationType.PROCESS,
                    message="未生成音频片段",
                    data={
                        "input_file": filename,
                        "target_duration": segment_duration_s,
                        "segments_generated": 0
                    },
                    warnings=["音频可能太短或无法检测到有效的节拍点"]
                ).to_dict()
            
            # 获取最终输出目录
            base_dir_manager = get_base_dir_manager()
            final_output_dir = base_dir_manager.get_base_dir() / "audio_output"
            
            # 清理并复制结果
            if final_output_dir.exists():
                shutil.rmtree(final_output_dir)
            shutil.copytree(processing_output_dir, final_output_dir)
            
            # 收集文件信息
            new_files = []
            segment_info = []
            total_size = 0
            
            for segment_path in segment_paths:
                # 获取最终路径
                final_path = final_output_dir / os.path.basename(segment_path)
                
                if final_path.exists():
                    file_size = final_path.stat().st_size
                    total_size += file_size
                    
                    # 获取相对路径
                    try:
                        base_path = Path(base_dir_manager.get_base_dir())
                        relative_path = final_path.relative_to(base_path)
                    except ValueError:
                        relative_path = Path("audio_output") / final_path.name
                    
                    # 创建文件信息
                    file_info = create_file_info(
                        path=str(relative_path),
                        description="音频片段",
                        size=file_size,
                        mime_type="audio/wav",
                        # 音频特定元数据
                        source_file=filename,
                        target_duration=segment_duration_s,
                        segment_index=len(new_files) + 1
                    )
                    new_files.append(file_info)
                    
                    # 片段信息用于data字段
                    segment_info.append({
                        "filename": final_path.name,
                        "path": str(relative_path),
                        "size": file_size,
                        "index": len(segment_info) + 1
                    })
            
            # 计算处理统计
            processing_stats = {
                "input_file": filename,
                "input_size": len(audio_data),
                "target_duration": segment_duration_s,
                "segments_generated": len(new_files),
                "total_output_size": total_size,
                "compression_ratio": total_size / len(audio_data) if len(audio_data) > 0 else 0,
                "segments": segment_info
            }
            
            return builder.success(
                operation=OperationType.PROCESS,
                message=f"成功将音频切分为 {len(new_files)} 个片段",
                data=processing_stats,
                new_files=new_files
            ).to_dict()
            
    except Exception as e:
        return builder.error(
            operation=OperationType.PROCESS,
            message="音频处理过程中发生未预期错误",
            error_details=f"系统错误: {type(e).__name__}: {str(e)}"
        ).to_dict()


@mcp.tool()
def get_audio_info(
    audio_file_content_base64: str,
    filename: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取音频文件的基本信息
    
    Args:
        audio_file_content_base64: base64编码的音频文件内容
        filename: 音频文件名
        session_id: 会话ID（可选）
    
    Returns:
        包含音频文件详细信息的标准响应
    """
    builder = MCPResponseBuilder("get_audio_info")
    
    try:
        # 解码音频数据
        try:
            audio_data = base64.b64decode(audio_file_content_base64)
        except Exception as e:
            return builder.error(
                operation=OperationType.QUERY,
                message="音频数据解码失败",
                error_details=f"base64解码错误: {str(e)}"
            ).to_dict()
        
        # 基本文件信息
        file_info = {
            "filename": filename,
            "size_bytes": len(audio_data),
            "size_readable": f"{len(audio_data) / 1024:.1f} KB" if len(audio_data) < 1024*1024 else f"{len(audio_data) / (1024*1024):.1f} MB",
            "file_extension": Path(filename).suffix.lower(),
        }
        
        # 尝试获取更详细的音频信息（如果可能）
        try:
            # 这里可以添加更高级的音频分析
            # 比如使用 librosa 或 pydub 获取采样率、时长等
            with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                
                # 这里可以添加音频分析逻辑
                # 目前返回基本信息
                audio_details = {
                    "format": "unknown",
                    "duration": "unknown",
                    "sample_rate": "unknown",
                    "channels": "unknown"
                }
                
        except Exception:
            audio_details = {
                "format": "unknown",
                "duration": "analysis_failed",
                "sample_rate": "analysis_failed",
                "channels": "analysis_failed"
            }
        
        # 合并信息
        complete_info = {**file_info, **audio_details}
        
        return builder.success(
            operation=OperationType.QUERY,
            message=f"成功获取音频文件 '{filename}' 的信息",
            data=complete_info
        ).to_dict()
        
    except Exception as e:
        return builder.error(
            operation=OperationType.QUERY,
            message="获取音频信息失败",
            error_details=str(e)
        ).to_dict()


@mcp.tool()
def list_supported_formats() -> Dict[str, Any]:
    """
    列出支持的音频格式
    
    Returns:
        支持的音频格式列表
    """
    builder = MCPResponseBuilder("list_supported_formats")
    
    supported_formats = {
        "input_formats": [
            {"extension": ".wav", "description": "WAV 无损音频格式", "recommended": True},
            {"extension": ".mp3", "description": "MP3 压缩音频格式", "recommended": True},
            {"extension": ".m4a", "description": "MPEG-4 音频格式", "recommended": False},
            {"extension": ".flac", "description": "FLAC 无损压缩格式", "recommended": False},
        ],
        "output_formats": [
            {"extension": ".wav", "description": "WAV 格式（默认输出）", "default": True}
        ],
        "features": {
            "beat_detection": "支持基于节拍的智能切分",
            "custom_duration": "支持自定义片段时长",
            "batch_processing": "支持批量处理（计划中）"
        },
        "limitations": {
            "max_file_size": "建议小于100MB",
            "min_duration": "建议至少10秒以上",
            "supported_sample_rates": "建议44.1kHz或48kHz"
        }
    }
    
    return builder.success(
        operation=OperationType.SYSTEM,
        message="音频处理服务支持的格式和功能",
        data=supported_formats
    ).to_dict()


@mcp.tool()
def get_service_status() -> Dict[str, Any]:
    """
    获取音频处理服务状态
    
    Returns:
        服务状态信息
    """
    builder = MCPResponseBuilder("get_service_status")
    
    try:
        # 检查依赖项
        dependencies = {
            "pydub": "unknown",
            "numpy": "unknown", 
            "scipy": "unknown"
        }
        
        # 检查输出目录
        base_dir_manager = get_base_dir_manager()
        output_dir = base_dir_manager.get_base_dir() / "audio_output"
        
        status_info = {
            "service": "audio_slicer",
            "status": "running",
            "version": "1.0.0-standard",
            "base_directory": str(base_dir_manager.get_base_dir()),
            "output_directory": str(output_dir),
            "output_directory_exists": output_dir.exists(),
            "dependencies": dependencies,
            "supported_operations": [
                "slice_audio_file",
                "get_audio_info", 
                "list_supported_formats",
                "get_service_status"
            ]
        }
        
        # 检查是否有处理过的文件
        if output_dir.exists():
            audio_files = list(output_dir.glob("*.wav"))
            status_info["processed_files_count"] = len(audio_files)
            status_info["last_processing"] = "recent" if audio_files else "none"
        
        return builder.success(
            operation=OperationType.SYSTEM,
            message="音频处理服务运行正常",
            data=status_info
        ).to_dict()
        
    except Exception as e:
        return builder.error(
            operation=OperationType.SYSTEM,
            message="无法获取服务状态",
            error_details=str(e)
        ).to_dict()


# 为了向后兼容，保留原有的函数名
@mcp.tool()
def slice_audio(
    audio_file_content_base64: str,
    filename: str,
    segment_duration_s: float,
    session_id: str = None,
) -> Dict[str, Any]:
    """
    音频切片实现函数（向后兼容）
    
    这是为了保持与现有代码的兼容性而保留的函数。
    实际功能委托给标准化的 slice_audio_file 函数。
    """
    return slice_audio_file(
        audio_file_content_base64=audio_file_content_base64,
        filename=filename,
        segment_duration_s=segment_duration_s,
        session_id=session_id
    )


# -----------------------------------------------------------------------------
# 服务器启动
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # 保持兼容性，使用原有启动方式
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
    from server_base import start_mcp_server
    
    print(f"🚀 启动标准化音频切片服务器")
    print(f"📁 基础目录: {get_base_dir()}")
    print(f"🌐 端口: {SERVER_PORT}")
    print(f"📋 使用标准响应格式")
    print(f"🎵 支持的操作: 音频切片、信息查询、格式检查")
    
    start_mcp_server(mcp, SERVER_PORT, SERVER_NAME)