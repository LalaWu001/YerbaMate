// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SimpleVault {
    address public owner;
    uint256 public totalAssets;
    uint256 public totalShares;
    uint256 public feeBps;
    mapping(address => uint256) public shares;

    event Deposit(address indexed user, uint256 assets, uint256 mintedShares);
    event Withdraw(address indexed user, uint256 sharesBurned, uint256 assets);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        require(msg.value > 0, "zero deposit");
        uint256 mintedShares = msg.value;
        shares[msg.sender] += mintedShares;
        totalShares += mintedShares;
        totalAssets += msg.value;
        emit Deposit(msg.sender, msg.value, mintedShares);
    }

    function withdraw(uint256 shareAmount) external {
        require(shares[msg.sender] >= shareAmount, "insufficient shares");
        uint256 assets = shareAmount;
        (bool ok, ) = msg.sender.call{value: assets}("");
        require(ok, "transfer failed");
        shares[msg.sender] -= shareAmount;
        totalShares -= shareAmount;
        totalAssets -= assets;
        emit Withdraw(msg.sender, shareAmount, assets);
    }

    function setFeeBps(uint256 newFeeBps) external onlyOwner {
        feeBps = newFeeBps;
    }
}
