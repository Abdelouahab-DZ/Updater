#!/bin/bash

# Define colors for UI styling
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================${NC}"
echo -e "${BLUE}    UBUNTU SYSTEM UPDATE    ${NC}"
echo -e "${BLUE}============================${NC}"

echo -e "\n${YELLOW}[+] Updating APT packages...${NC}"
sudo apt update && sudo apt full-upgrade -y

echo -e "\n${YELLOW}[+] Cleaning up unused dependencies...${NC}"
sudo apt autoremove -y
sudo apt clean

if command -v snap &> /dev/null; then
    echo -e "\n${YELLOW}[+] Refreshing Snap packages...${NC}"
    sudo snap refresh
fi

if command -v flatpak &> /dev/null; then
    echo -e "\n${YELLOW}[+] Refreshing Flatpak packages...${NC}"
    flatpak update -y
fi

echo -e "\n${GREEN}============================${NC}"
echo -e "${GREEN}    UPDATE COMPLETE! 🎉     ${NC}"
echo -e "${GREEN}============================${NC}"

read -p "Press Enter to exit..."
