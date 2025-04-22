#!/bin/bash

echo "🔍 Looking for latest Flet Flutter build directory..."
FLET_DIR=$(find /private/var/folders -type d -name "flet_flutter_build_*" 2>/dev/null | sort -r | head -n 1)

if [ -z "$FLET_DIR" ]; then
    echo "❌ Could not find any Flet Flutter build directories."
    exit 1
fi

WRAPPER_FILE="$FLET_DIR/android/gradle/wrapper/gradle-wrapper.properties"

if [ ! -f "$WRAPPER_FILE" ]; then
    echo "❌ gradle-wrapper.properties not found at $WRAPPER_FILE"
    exit 1
fi

echo "✅ Found: $WRAPPER_FILE"
echo "⚙️ Updating Gradle version to 8.5..."

sed -i '' 's|distributionUrl=.*|distributionUrl=https\\://services.gradle.org/distributions/gradle-8.5-bin.zip|' "$WRAPPER_FILE"

echo "🎉 Gradle wrapper updated successfully!"
