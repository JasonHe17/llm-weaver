#!/bin/bash
# 运行测试脚本

cd "$(dirname "$0")"

echo "=========================================="
echo "Running LLM Weaver Tests"
echo "=========================================="

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: Not in a virtual environment"
fi

# 运行测试
echo ""
echo "Running pytest..."
pytest "$@"

# 获取测试结果
TEST_RESULT=$?

echo ""
echo "=========================================="
if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed"
fi
echo "=========================================="

exit $TEST_RESULT
