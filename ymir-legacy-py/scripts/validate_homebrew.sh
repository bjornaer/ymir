#!/bin/bash
# Validate Homebrew formula locally before pushing

set -e

echo "========================================="
echo "Homebrew Formula Validation Script"
echo "========================================="
echo

# Check if formula file exists
if [ ! -f "Formula/ymir.rb" ] && [ ! -f "ymir.rb" ]; then
    echo "Error: Formula file not found (ymir.rb or Formula/ymir.rb)"
    exit 1
fi

FORMULA_FILE="Formula/ymir.rb"
if [ ! -f "$FORMULA_FILE" ]; then
    FORMULA_FILE="ymir.rb"
fi

echo "Formula file: $FORMULA_FILE"
echo

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Error: Homebrew is not installed"
    echo "Install from: https://brew.sh"
    exit 1
fi

echo "Homebrew version:"
brew --version
echo

# Validate formula syntax
echo "Step 1: Validating formula syntax..."
brew audit --strict "$FORMULA_FILE" || {
    echo "Warning: Formula has audit issues (see above)"
}
echo "✓ Syntax validation complete"
echo

# Style check
echo "Step 2: Checking formula style..."
brew style "$FORMULA_FILE" || {
    echo "Warning: Formula has style issues (see above)"
}
echo "✓ Style check complete"
echo

# Test installation (optional)
read -p "Do you want to test installation? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Step 3: Testing installation..."
    
    # Uninstall if already installed
    brew uninstall ymir 2>/dev/null || true
    
    # Install from formula
    brew install --build-from-source "$FORMULA_FILE"
    
    # Test the installation
    echo "Testing ymir command..."
    ymir --version
    ymir --help
    
    echo "✓ Installation test complete"
    echo
    
    # Clean up
    read -p "Do you want to uninstall the test installation? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        brew uninstall ymir
        echo "✓ Test installation cleaned up"
    fi
fi

echo
echo "========================================="
echo "Validation complete!"
echo "========================================="

