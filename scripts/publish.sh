#!/bin/bash
# 发布所有包到 PyPI 的脚本
# 使用方法: ./scripts/publish.sh [package-name] [--test]

set -e

# 配置
PACKAGES=("pi_ai" "pi_agent" "pi_tui" "pi_coding")
TEST_MODE=false

# 解析参数
if [ "$1" == "--test" ]; then
    TEST_MODE=true
    shift
elif [ "$2" == "--test" ]; then
    TEST_MODE=true
fi

# 指定单个包或全部
if [ -n "$1" ]; then
    PACKAGES=("$1")
fi

# PyPI 地址
if [ "$TEST_MODE" = true ]; then
    PYPI_URL="https://test.pypi.org/simple/"
    echo "🧪 测试模式: 将发布到 TestPyPI"
else
    PYPI_URL="https://pypi.org/simple/"
    echo "🚀 正式模式: 将发布到 PyPI"
fi

# 发布顺序（按依赖关系）
ORDERED_PACKAGES=("pi_ai" "pi_agent" "pi_tui" "pi_coding")

for pkg in "${ORDERED_PACKAGES[@]}"; do
    # 检查是否在要发布的列表中
    skip=true
    for p in "${PACKAGES[@]}"; do
        if [ "$p" == "$pkg" ]; then
            skip=false
            break
        fi
    done
    
    if [ "$skip" = true ]; then
        continue
    fi
    
    echo ""
    echo "========================================="
    echo "📦 处理包: $pkg"
    echo "========================================="
    
    PKG_DIR="packages/$pkg"
    
    # 清理旧的构建文件
    echo "🧹 清理旧的构建文件..."
    rm -rf "$PKG_DIR/dist" "$PKG_DIR/build"
    
    # 构建
    echo "🔨 构建包..."
    uv build "$PKG_DIR"
    
    # 检查构建结果
    if [ ! -d "$PKG_DIR/dist" ]; then
        echo "❌ 构建失败: $pkg"
        exit 1
    fi
    
    # 显示构建的文件
    echo "📁 构建文件:"
    ls -la "$PKG_DIR/dist/"
    
    # 发布
    echo "📤 发布到 PyPI..."
    if [ "$TEST_MODE" = true ]; then
        uv publish --index-url "https://test.pypi.org/legacy/" "$PKG_DIR/dist/*"
    else
        uv publish "$PKG_DIR/dist/*"
    fi
    
    echo "✅ 完成: $pkg"
    
    # 等待一下，让 PyPI 处理
    sleep 5
done

echo ""
echo "========================================="
echo "🎉 所有包发布完成!"
echo "========================================="
