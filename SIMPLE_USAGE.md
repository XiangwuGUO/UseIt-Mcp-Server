# 简化的MCP + FRP集成使用说明

## 概述

这个简化方案专门解决**服务器端MCP客户端无法连接到客户机端MCP服务器**的问题。

- **问题**: 客户机上运行MCP服务器，服务器上运行MCP客户端，由于NAT/防火墙无法直接连接
- **解决方案**: 在MCP服务器注册时可选择使用FRP反向代理，让服务器端客户端通过公网地址连接

## 架构图

```
[客户机] MCP服务器 ←→ FRP隧道 ←→ [公网] ←→ [服务器] MCP客户端
```

## 使用方法

### 1. 本地测试模式 (无FRP)

```bash
# 启动所有服务器 (本地模式)
./start_simple_servers.sh start

# 启动单个服务器测试
./start_simple_servers.sh single audio_slicer

# 查看状态
./start_simple_servers.sh status
```

### 2. FRP远程注册模式

```bash
# 设置MCP客户端地址 (服务器端)
export MCP_CLIENT_URL="http://your-server:8080"

# 启动服务器并自动创建FRP隧道注册
./start_simple_servers.sh start-frp

# 启动单个服务器 (FRP模式)
./start_simple_servers.sh single-frp filesystem
```

### 3. 管理命令

```bash
# 停止所有服务器
./start_simple_servers.sh stop

# 重启 (FRP模式)
./start_simple_servers.sh restart-frp

# 查看日志
./start_simple_servers.sh logs

# 列出可用服务器
./start_simple_servers.sh list
```

## 工作流程

### 客户机端操作 (运行MCP服务器)

1. **本地开发测试**:
   ```bash
   # 本地测试，不使用FRP
   ./start_simple_servers.sh start
   ```

2. **远程部署**:
   ```bash
   # 设置服务器端MCP客户端地址
   export MCP_CLIENT_URL="http://your-server.com:8080"
   
   # 启动服务器并创建FRP隧道
   ./start_simple_servers.sh start-frp
   ```

3. **服务器自动注册过程**:
   - 启动本地MCP服务器 (如 localhost:8002)
   - 创建FRP隧道 (如 https://abc123.useit.run → localhost:8002)  
   - 向服务器端MCP客户端注册公网地址 (https://abc123.useit.run/mcp)
   - 服务器端客户端现在可以通过公网地址连接

### 服务器端操作 (运行MCP客户端)

服务器端无需特殊操作，MCP客户端会自动接收来自客户机的服务器注册，并使用公网地址连接。

## 特点

### ✅ 优势

1. **保持兼容**: 完全兼容原有本地测试流程
2. **最小侵入**: 只在注册时使用FRP，不影响核心MCP协议
3. **可选功能**: FRP功能完全可选，默认本地模式
4. **开源友好**: MCP服务器部分可以开源，FRP只是部署时的可选功能
5. **一键启动**: 保持一键启动能力，只是多了FRP选项

### 📋 使用场景

- **开发测试**: 使用本地模式 (`./start_simple_servers.sh start`)
- **远程部署**: 使用FRP模式 (`./start_simple_servers.sh start-frp`)
- **混合环境**: 部分服务器使用FRP，部分使用本地

## 代码结构

```
useit-mcp/
├── mcp-server/
│   ├── simple_frp_registry.py    # FRP注册器
│   ├── simple_launcher.py        # 简化启动器  
│   └── official_server/          # MCP服务器实现
├── start_simple_servers.sh       # 统一启动脚本
└── SIMPLE_USAGE.md              # 本文档
```

### 核心模块说明

- **simple_frp_registry.py**: 负责FRP隧道创建和服务器注册
- **simple_launcher.py**: 简化的服务器启动器，支持可选FRP
- **start_simple_servers.sh**: 统一管理脚本，支持本地和FRP模式

## 环境变量

```bash
# MCP客户端地址 (服务器端)
export MCP_CLIENT_URL="http://localhost:8080"

# 或者在启动时指定
./start_simple_servers.sh start-frp --registry-url http://your-server:8080
```

## 故障排除

### FRP连接失败
```bash
# 检查FRP服务器连通性
ping useit.run

# 查看详细日志
./start_simple_servers.sh logs
```

### 注册失败
```bash
# 检查MCP客户端地址是否正确
echo $MCP_CLIENT_URL

# 手动测试注册接口
curl -X POST $MCP_CLIENT_URL/servers/register -d '{"name":"test"}'
```

### 服务器启动失败
```bash
# 查看详细状态
./start_simple_servers.sh status

# 查看错误日志
./start_simple_servers.sh logs
```

## 示例脚本

### 快速测试脚本

```bash
#!/bin/bash
# quick_test.sh - 快速测试脚本

echo "1. 启动本地模式测试..."
./start_simple_servers.sh single audio_slicer
sleep 5

echo "2. 测试完成，启动FRP模式..."  
./start_simple_servers.sh stop
export MCP_CLIENT_URL="http://localhost:8080"
./start_simple_servers.sh single-frp audio_slicer
```

这个简化方案专注解决核心问题，保持了原有的简洁性和可用性。