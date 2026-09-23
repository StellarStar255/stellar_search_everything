#!/bin/bash
# 本地构建 + Developer ID 签名 + 公证 + staple，并替换 GitHub Release 上的 macOS DMG。
#
# 用法: ./packaging/macos/release_macos.sh v1.6.13
#
# 前置条件（均为一次性配置）:
#   - 钥匙串中有 "Developer ID Application" 证书
#   - 已配置公证凭据: xcrun notarytool store-credentials notary \
#         --apple-id <AppleID邮箱> --team-id <TeamID>
#   - 已安装 gh 并登录；对应 tag 的 Release 已由 CI 创建
set -euo pipefail

TAG=${1:?用法: $0 vX.Y.Z}
SIGN_ID="Developer ID Application: Qiliang Huang (3QCL9WNFBB)"
NOTARY_PROFILE="notary"
APP_NAME="Stellar Search Everything"
DMG_NAME="StellarSearchEverything-${TAG}-macos-arm64.dmg"

REPO_DIR=$(cd "$(dirname "$0")/../.." && pwd)
WORK_DIR=$(mktemp -d /tmp/stellar-search-release.XXXXXX)
trap 'rm -rf "$WORK_DIR"' EXIT
cd "$REPO_DIR"

echo "==> [1/6] PyInstaller 构建"
python3 -m PyInstaller --noconfirm --windowed --name "$APP_NAME" \
  --icon "$REPO_DIR/assets/AppIcon.icns" \
  --add-data "$REPO_DIR/assets/icon.png:assets" \
  --add-data "$REPO_DIR/assets/check.svg:assets" \
  --add-data "$REPO_DIR/assets/chevron.svg:assets" \
  --distpath "$WORK_DIR/dist" --workpath "$WORK_DIR/build" \
  --specpath "$WORK_DIR" FileSearchQt.py
APP="$WORK_DIR/dist/$APP_NAME.app"

echo "==> [2/6] Developer ID 签名（hardened runtime）"
find "$APP/Contents" -type f \( -name "*.dylib" -o -name "*.so" \) \
  -exec codesign --force --timestamp --options runtime --sign "$SIGN_ID" {} +
codesign --force --timestamp --options runtime \
  --entitlements "$REPO_DIR/packaging/macos/entitlements.plist" \
  --sign "$SIGN_ID" "$APP"
codesign --verify --deep --strict "$APP"

echo "==> [3/6] 制作并签名 DMG"
mkdir "$WORK_DIR/dmg-staging"
cp -R "$APP" "$WORK_DIR/dmg-staging/"
ln -s /Applications "$WORK_DIR/dmg-staging/Applications"
hdiutil create -volname "$APP_NAME" -srcfolder "$WORK_DIR/dmg-staging" \
  -ov -format UDZO "$WORK_DIR/$DMG_NAME"
codesign --force --timestamp --sign "$SIGN_ID" "$WORK_DIR/$DMG_NAME"

echo "==> [4/6] 提交 Apple 公证（通常几分钟）"
xcrun notarytool submit "$WORK_DIR/$DMG_NAME" \
  --keychain-profile "$NOTARY_PROFILE" --wait

echo "==> [5/6] Staple 公证票据"
xcrun stapler staple "$WORK_DIR/$DMG_NAME"
spctl --assess --type open --context context:primary-signature -v "$WORK_DIR/$DMG_NAME"

echo "==> [6/6] 替换 Release 上的 DMG"
gh release upload "$TAG" "$WORK_DIR/$DMG_NAME" --clobber

echo "完成: $TAG 的 macOS DMG 已签名 + 公证并上传"
