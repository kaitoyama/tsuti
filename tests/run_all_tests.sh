#!/bin/bash
# 全テストを実行するスクリプト

set -e
cd "$(dirname "$0")/.."

echo "=== 1. 部分改正モードのテスト ==="
python3 tests/test_partial_apply.py

echo ""
echo "=== 2. 部分改正モードでの参照追従テスト ==="
python3 tests/test_partial_refs.py

echo ""
echo "=== 3. サンプルファイルでの完全適用テスト ==="
cd examples
python3 ../shinkyu.py apply sample.tsuchi.txt sample_改正.shinkyu.txt \
    -o /tmp/sample_v2_test.tsuchi.txt \
    --patch-out /tmp/sample_改正_完成版_test.shinkyu.txt
cd ..

echo ""
echo "=== すべてのテストが成功しました ==="
