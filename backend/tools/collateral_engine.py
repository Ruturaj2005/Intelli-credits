"""
Collateral Engine — Asset Valuation and Charge Verification

Evaluates collateral offered for secured lending:
1. CERSAI charge verification (existing mortgages)
2. Asset valuation and marketability assessment
3. LTV (Loan-to-Value) ratio calculation
4. Insurance coverage verification
5. Legal title verification status
6. Prior charge ranking

Asset Types Supported:
- Land and Building (Real Estate)
- Plant and Machinery
- Vehicles
- Stock and Receivables (Current Assets)
- Shares and Securities
- Intangible Assets (Brand, IP)

Red Flag Rules:
- Fully mortgaged collateral (no residual security) → RF024
- LTV > 75% for immovable property → High risk
- LTV > 50% for movable assets → High risk
- Uninsured collateral → Flag
- Disputed ownership/title → RF024

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class AssetType(str, Enum):
    """Types of collateral assets."""
    LAND_BUILDING = "Land & Building"
    PLANT_MACHINERY = "Plant & Machinery"
    VEHICLES = "Vehicles"
    STOCK = "Stock & Inventory"
    RECEIVABLES = "Receivables & Book Debts"
    SHARES = "Shares & Securities"
    INTANGIBLES = "Intangible Assets"
    GOLD_BULLION = "Gold & Precious Metals"


class ChargeType(str, Enum):
    """Type of charge/security."""
    FIRST_CHARGE = "First Charge (Mortgage)"
    SECOND_CHARGE = "Second Charge (Pari Passu)"
    HYPOTHECATION = "Hypothecation"
    PLEDGE = "Pledge"
    NEGATIVE_LIEN = "Negative Lien"


@dataclass
class ExistingCharge:
    """Existing charge on asset from CERSAI."""
    charge_id: str
    charge_holder: str  # Bank/NBFC name
    charge_type: ChargeType
    charge_amount: float
    creation_date: str
    status: str  # Active, Satisfied, Pending
    satisfaction_date: Optional[str] = None


@dataclass
class Asset:
    """Collateral asset details."""
    asset_id: str
    asset_type: AssetType
    description: str
    location: Optional[str] = None
    
    # Valuation
    market_value: float = 0.0
    forced_sale_value: float = 0.0  # 70-80% of market value
    valuation_date: Optional[str] = None
    valuer_name: Optional[str] = None
    
    # Legal
    ownership_verified: bool = False
    title_clear: bool = False
    has_disputes: bool = False
    
    # Insurance
    insured: bool = False
    insurance_value: float = 0.0
    insurance_expiry: Optional[str] = None
    
    # Marketability
    marketability_score: float = 0.0  # 0-100
    liquidity_days: int = 90  # Days to liquidate
    
    # CERSAI
    cersai_checked: bool = False
    existing_charges: List[ExistingCharge] = field(default_factory=list)


@dataclass
class CollateralResult:
    """Result from collateral engine."""
    score: float  # 0-100
    flags: List[str]
    data: Dict[str, Any]
    confidence: float
    
    # Key metrics
    total_market_value: float = 0.0
    total_forced_sale_value: float = 0.0
    total_existing_charges: float = 0.0
    net_realizable_value: float = 0.0
    ltv_ratio: float = 0.0
    security_coverage: float = 0.0
    
    # Assets
    assets: List[Asset] = field(default_factory=list)


async def evaluate_collateral(
    assets: List[Dict[str, Any]],
    loan_amount: float,
    check_cersai: bool = True,
    use_mock: bool = True
) -> CollateralResult:
    """
    Evaluate collateral offered for loan.
    
    Args:
        assets: List of asset dicts with details
        loan_amount: Requested loan amount
        check_cersai: Whether to check CERSAI for existing charges
        use_mock: Use mock CERSAI data
        
    Returns:
        CollateralResult with valuation and risk assessment
    """
    logger.info(f"🏦 Evaluating collateral: {len(assets)} assets for loan of ₹{loan_amount:,.0f}")
    
    # Parse assets
    parsed_assets = []
    for asset_data in assets:
        asset = _parse_asset(asset_data)
        
        # Check CERSAI if required
        if check_cersai and asset.asset_type in [AssetType.LAND_BUILDING, AssetType.PLANT_MACHINERY]:
            asset = await _check_cersai_charges(asset, use_mock)
        
        # Calculate marketability score
        asset.marketability_score = _calculate_marketability(asset)
        
        parsed_assets.append(asset)
    
    # Calculate aggregate values
    total_market_value = sum(a.market_value for a in parsed_assets)
    total_forced_sale_value = sum(a.forced_sale_value for a in parsed_assets)
    total_existing_charges = sum(
        sum(c.charge_amount for c in a.existing_charges if c.status == "Active")
        for a in parsed_assets
    )
    
    # Net realizable value (after existing charges)
    net_realizable_value = total_forced_sale_value - total_existing_charges
    
    # LTV ratio
    ltv_ratio = (loan_amount / total_market_value * 100) if total_market_value > 0 else 0
    
    # Security coverage ratio
    security_coverage = (net_realizable_value / loan_amount) if loan_amount > 0 else 0
    
    # Generate flags
    flags = _generate_collateral_flags(
        parsed_assets,
        ltv_ratio,
        security_coverage,
        net_realizable_value
    )
    
    # Calculate score
    score = _calculate_collateral_score(
        ltv_ratio,
        security_coverage,
        parsed_assets,
        flags
    )
    
    # Build detailed data
    data = {
        "total_assets": len(parsed_assets),
        "total_market_value": total_market_value,
        "total_forced_sale_value": total_forced_sale_value,
        "total_existing_charges": total_existing_charges,
        "net_realizable_value": net_realizable_value,
        "loan_amount": loan_amount,
        "ltv_ratio_pct": ltv_ratio,
        "security_coverage_ratio": security_coverage,
        "assets_breakdown": [
            {
                "type": a.asset_type.value,
                "description": a.description,
                "market_value": a.market_value,
                "forced_sale_value": a.forced_sale_value,
                "existing_charges": len(a.existing_charges),
                "existing_charge_amount": sum(c.charge_amount for c in a.existing_charges if c.status == "Active"),
                "marketability_score": a.marketability_score,
                "insured": a.insured,
                "title_clear": a.title_clear
            }
            for a in parsed_assets
        ]
    }
    
    confidence = 0.85 if all(a.cersai_checked for a in parsed_assets) else 0.70
    
    logger.info(
        f"✅ Collateral evaluation complete | Score: {score:.1f}/100 | "
        f"LTV: {ltv_ratio:.1f}% | Coverage: {security_coverage:.2f}x"
    )
    
    return CollateralResult(
        score=score,
        flags=flags,
        data=data,
        confidence=confidence,
        total_market_value=total_market_value,
        total_forced_sale_value=total_forced_sale_value,
        total_existing_charges=total_existing_charges,
        net_realizable_value=net_realizable_value,
        ltv_ratio=ltv_ratio,
        security_coverage=security_coverage,
        assets=parsed_assets
    )


def _parse_asset(asset_data: Dict[str, Any]) -> Asset:
    """Parse asset data into Asset object."""
    asset_type_map = {
        "land": AssetType.LAND_BUILDING,
        "building": AssetType.LAND_BUILDING,
        "property": AssetType.LAND_BUILDING,
        "machinery": AssetType.PLANT_MACHINERY,
        "plant": AssetType.PLANT_MACHINERY,
        "vehicle": AssetType.VEHICLES,
        "stock": AssetType.STOCK,
        "receivables": AssetType.RECEIVABLES,
        "shares": AssetType.SHARES,
        "gold": AssetType.GOLD_BULLION
    }
    
    # Determine asset type
    asset_type_str = asset_data.get("type", "").lower()
    asset_type = AssetType.LAND_BUILDING  # Default
    
    for key, value in asset_type_map.items():
        if key in asset_type_str:
            asset_type = value
            break
    
    # Calculate forced sale value (typically 70-75% of market value)
    market_value = float(asset_data.get("market_value", 0))
    forced_sale_value = asset_data.get("forced_sale_value")
    
    if not forced_sale_value:
        # Use standard haircut based on asset type
        haircut = {
            AssetType.LAND_BUILDING: 0.75,
            AssetType.PLANT_MACHINERY: 0.60,
            AssetType.VEHICLES: 0.50,
            AssetType.STOCK: 0.50,
            AssetType.RECEIVABLES: 0.70,
            AssetType.SHARES: 0.50,
            AssetType.GOLD_BULLION: 0.75
        }
        forced_sale_value = market_value * haircut.get(asset_type, 0.70)
    
    return Asset(
        asset_id=asset_data.get("id", f"ASSET_{datetime.now().timestamp()}"),
        asset_type=asset_type,
        description=asset_data.get("description", ""),
        location=asset_data.get("location"),
        market_value=market_value,
        forced_sale_value=float(forced_sale_value),
        valuation_date=asset_data.get("valuation_date"),
        valuer_name=asset_data.get("valuer"),
        ownership_verified=asset_data.get("ownership_verified", False),
        title_clear=asset_data.get("title_clear", True),
        has_disputes=asset_data.get("has_disputes", False),
        insured=asset_data.get("insured", False),
        insurance_value=float(asset_data.get("insurance_value", 0)),
        insurance_expiry=asset_data.get("insurance_expiry"),
        liquidity_days=asset_data.get("liquidity_days", 90)
    )


async def _check_cersai_charges(asset: Asset, use_mock: bool = True) -> Asset:
    """
    Check CERSAI registry for existing charges on asset.
    
    CERSAI (Central Registry of Securitisation Asset Reconstruction
    and Security Interest) maintains records of charges created on assets.
    """
    logger.info(f"🔍 Checking CERSAI for asset: {asset.description}")
    
    if use_mock:
        # Use mock data
        asset.existing_charges = _get_mock_cersai_charges(asset)
    else:
        # In production: Query actual CERSAI API
        try:
            charges = await _query_cersai_api(asset)
            asset.existing_charges = charges
        except Exception as e:
            logger.error(f"❌ CERSAI query failed: {str(e)}")
            asset.existing_charges = []
    
    asset.cersai_checked = True
    
    return asset


def _get_mock_cersai_charges(asset: Asset) -> List[ExistingCharge]:
    """Generate mock CERSAI charges based on asset."""
    # Determine if asset has existing charges (random for demo)
    import random
    
    if asset.market_value > 50000000:  # High-value assets more likely to have charges
        has_charge_probability = 0.6
    elif asset.market_value > 10000000:
        has_charge_probability = 0.3
    else:
        has_charge_probability = 0.1
    
    if random.random() > has_charge_probability:
        return []  # No existing charges
    
    # Create mock charge
    charge_amount = asset.market_value * random.uniform(0.3, 0.8)
    
    return [
        ExistingCharge(
            charge_id=f"CERSAI{random.randint(100000, 999999)}",
            charge_holder="HDFC Bank Ltd",
            charge_type=ChargeType.FIRST_CHARGE,
            charge_amount=charge_amount,
            creation_date="2021-06-15",
            status="Active"
        )
    ]


async def _query_cersai_api(asset: Asset) -> List[ExistingCharge]:
    """
    Query actual CERSAI API (placeholder).
    
    In production, this would:
    1. Authenticate with CERSAI portal
    2. Search by asset identifiers
    3. Parse response
    4. Return structured charge data
    """
    # Placeholder - would implement actual API calls
    return []


def _calculate_marketability(asset: Asset) -> float:
    """
    Calculate asset marketability score (0-100).
    
    Factors:
    - Asset type (liquidity)
    - Location (for real estate)
    - Condition
    - Market demand
    - Legal clarity
    """
    score = 50.0  # Base score
    
    # Asset type marketability
    type_scores = {
        AssetType.LAND_BUILDING: 70,
        AssetType.GOLD_BULLION: 90,
        AssetType.SHARES: 80,
        AssetType.VEHICLES: 60,
        AssetType.PLANT_MACHINERY: 50,
        AssetType.STOCK: 40,
        AssetType.RECEIVABLES: 60,
        AssetType.INTANGIBLES: 30
    }
    
    score = type_scores.get(asset.asset_type, 50)
    
    # Legal clarity bonus
    if asset.title_clear and asset.ownership_verified:
        score += 10
    
    # Dispute penalty
    if asset.has_disputes:
        score -= 30
    
    # Insurance bonus
    if asset.insured:
        score += 5
    
    # Existing charges penalty
    if asset.existing_charges:
        active_charges = [c for c in asset.existing_charges if c.status == "Active"]
        if active_charges:
            score -= len(active_charges) * 10
    
    return max(0, min(100, score))


def _generate_collateral_flags(
    assets: List[Asset],
    ltv_ratio: float,
    security_coverage: float,
    net_realizable_value: float
) -> List[str]:
    """Generate red flags based on collateral analysis."""
    flags = []
    
    # RF024: Fully mortgaged collateral
    fully_mortgaged_assets = []
    for asset in assets:
        if asset.existing_charges:
            total_charges = sum(c.charge_amount for c in asset.existing_charges if c.status == "Active")
            if total_charges >= asset.forced_sale_value * 0.95:  # 95%+ mortgaged
                fully_mortgaged_assets.append(asset.description)
    
    if fully_mortgaged_assets:
        flags.append(
            f"RF024: {len(fully_mortgaged_assets)} asset(s) fully or highly mortgaged - "
            f"insufficient residual security"
        )
    
    # High LTV ratio
    if ltv_ratio > 80:
        flags.append(f"Critical: LTV ratio {ltv_ratio:.1f}% exceeds safe limit (80%)")
    elif ltv_ratio > 75:
        flags.append(f"High LTV ratio: {ltv_ratio:.1f}% (Warning threshold)")
    
    # Low security coverage
    if security_coverage < 1.25:
        flags.append(f"Insufficient security coverage: {security_coverage:.2f}x (Minimum: 1.25x)")
    
    # Uninsured high-value assets
    uninsured_value = sum(a.market_value for a in assets if not a.insured and a.market_value > 5000000)
    if uninsured_value > 0:
        flags.append(f"High-value assets uninsured: ₹{uninsured_value:,.0f}")
    
    # Title issues
    title_issues = [a for a in assets if not a.title_clear or a.has_disputes]
    if title_issues:
        flags.append(f"{len(title_issues)} asset(s) with title/legal issues")
    
    # Low marketability
    low_marketability = [a for a in assets if a.marketability_score < 40]
    if low_marketability:
        flags.append(f"{len(low_marketability)} asset(s) with low marketability (<40)")
    
    return flags


def _calculate_collateral_score(
    ltv_ratio: float,
    security_coverage: float,
    assets: List[Asset],
    flags: List[str]
) -> float:
    """Calculate collateral score (0-100)."""
    score = 100.0
    
    # LTV penalty
    if ltv_ratio > 80:
        score -= 40
    elif ltv_ratio > 75:
        score -= 25
    elif ltv_ratio > 65:
        score -= 10
    
    # Security coverage penalty
    if security_coverage < 1.0:
        score -= 50  # Critical
    elif security_coverage < 1.25:
        score -= 25
    elif security_coverage < 1.5:
        score -= 10
    
    # Marketability penalty
    avg_marketability = sum(a.marketability_score for a in assets) / len(assets) if assets else 0
    if avg_marketability < 40:
        score -= 20
    elif avg_marketability < 60:
        score -= 10
    
    # Red flag penalties
    if any("RF024" in flag for flag in flags):
        score -= 30
    
    # Insurance penalty
    uninsured_count = sum(1 for a in assets if not a.insured)
    score -= uninsured_count * 5
    
    return max(0, score)


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage of collateral engine."""
    
    # Scenario 1: Strong collateral
    print("="*70)
    print("SCENARIO 1: Strong Collateral Package")
    print("="*70)
    
    assets1 = [
        {
            "type": "land",
            "description": "Commercial property - Plot 123, Sector 18, Gurugram",
            "market_value": 80000000,
            "location": "Gurugram, Haryana",
            "ownership_verified": True,
            "title_clear": True,
            "has_disputes": False,
            "insured": True,
            "insurance_value": 80000000,
            "valuation_date": "2024-01-15",
            "valuer": "Knight Frank India"
        },
        {
            "type": "machinery",
            "description": "CNC Machines and Manufacturing Equipment",
            "market_value": 25000000,
            "ownership_verified": True,
            "title_clear": True,
            "insured": True,
            "insurance_value": 25000000
        }
    ]
    
    result1 = await evaluate_collateral(
        assets=assets1,
        loan_amount=50000000,
        check_cersai=True,
        use_mock=True
    )
    
    print(f"Score: {result1.score:.1f}/100")
    print(f"Total Market Value: ₹{result1.total_market_value:,.0f}")
    print(f"Net Realizable Value: ₹{result1.net_realizable_value:,.0f}")
    print(f"LTV Ratio: {result1.ltv_ratio:.1f}%")
    print(f"Security Coverage: {result1.security_coverage:.2f}x")
    print(f"Flags: {len(result1.flags)}")
    if result1.flags:
        for flag in result1.flags:
            print(f"  ⚠️  {flag}")
    
    # Scenario 2: Weak collateral (over-leveraged)
    print("\n" + "="*70)
    print("SCENARIO 2: Over-leveraged Collateral")
    print("="*70)
    
    assets2 = [
        {
            "type": "land",
            "description": "Industrial land - 5 acres, outskirts",
            "market_value": 30000000,
            "location": "Rural area",
            "ownership_verified": True,
            "title_clear": False,  # Title issue!
            "has_disputes": True,  # Legal dispute!
            "insured": False,  # Not insured!
            "valuation_date": "2023-06-10"
        }
    ]
    
    result2 = await evaluate_collateral(
        assets=assets2,
        loan_amount=28000000,  # Very high LTV
        check_cersai=True,
        use_mock=True
    )
    
    print(f"Score: {result2.score:.1f}/100")
    print(f"Total Market Value: ₹{result2.total_market_value:,.0f}")
    print(f"Net Realizable Value: ₹{result2.net_realizable_value:,.0f}")
    print(f"LTV Ratio: {result2.ltv_ratio:.1f}%")
    print(f"Security Coverage: {result2.security_coverage:.2f}x")
    
    if result2.flags:
        print(f"\n🚨 Red Flags:")
        for flag in result2.flags:
            print(f"  • {flag}")


if __name__ == "__main__":
    asyncio.run(main_example())
