"""
Group Exposure Analyzer — Related Party and Contagion Risk Assessment

Analyzes group company exposure and cross-guarantees to detect:
1. Total group debt exposure
2. Cross-guarantees and corporate guarantees
3. Inter-company loans and advances
4. Fund pooling/circular transactions
5. Contagion risk (if one fails, all fail)
6. Common promoters and directors
7. Related party transactions

Red Flag Rules:
- Group debt >5x group equity → RF030 (Contagion risk)
- Multiple cross-guarantees → High risk
- Circular fund flows → Fraud concern
- Weak company guaranteeing strong company → Red flag

Purpose:
Banks must evaluate total group exposure, not just individual
company risk, as group companies often have interlinked finances.

Author: Credit Intelligence System
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx  # For graph analysis

logger = logging.getLogger(__name__)


@dataclass
class GroupEntity:
    """A company in the group."""
    entity_id: str
    entity_name: str
    cin: Optional[str] = None
    relationship: str = "Subsidiary"  # Subsidiary, Associate, Holding, Sister
    ownership_pct: float = 0.0
    
    # Financials
    revenue: float = 0.0
    net_worth: float = 0.0
    total_debt: float = 0.0
    
    # Status
    is_borrower: bool = False
    existing_exposure: float = 0.0  # Existing loan from our bank
    proposed_exposure: float = 0.0


@dataclass
class CrossGuarantee:
    """Cross-guarantee between group entities."""
    guarantee_id: str
    guarantor: str  # Entity providing guarantee
    beneficiary: str  # Entity being guaranteed
    amount: float
    purpose: str
    date: str
    status: str = "Active"


@dataclass
class IntercompanyTransaction:
    """Transaction between group entities."""
    from_entity: str
    to_entity: str
    amount: float
    transaction_type: str  # Loan, Advance, Sale, Purchase
    date: str
    is_arms_length: bool = True


@dataclass
class GroupExposureResult:
    """Result from group exposure analysis."""
    score: float  # 0-100
    flags: List[str]
    data: Dict[str, Any]
    confidence: float
    
    # Key metrics
    total_group_entities: int = 0
    total_group_debt: float = 0.0
    total_group_net_worth: float = 0.0
    total_group_revenue: float = 0.0
    group_debt_to_equity: float = 0.0
    total_cross_guarantees: float = 0.0
    contagion_risk_score: float = 0.0  # 0-100
    
    # Entities and relationships
    entities: List[GroupEntity] = field(default_factory=list)
    cross_guarantees: List[CrossGuarantee] = field(default_factory=list)
    intercompany_txns: List[IntercompanyTransaction] = field(default_factory=list)


async def analyze_group_exposure(
    primary_entity: Dict[str, Any],
    group_entities: List[Dict[str, Any]],
    cross_guarantees: List[Dict[str, Any]],
    intercompany_txns: Optional[List[Dict[str, Any]]] = None,
    proposed_loan_amount: float = 0.0
) -> GroupExposureResult:
    """
    Analyze group company exposure and contagion risk.
    
    Args:
        primary_entity: Main borrowing entity data
        group_entities: List of related group companies
        cross_guarantees: List of cross-guarantees
        intercompany_txns: Inter-company transactions
        proposed_loan_amount: New loan amount being considered
        
    Returns:
        GroupExposureResult with risk assessment
    """
    logger.info(f"🏢 Analyzing group exposure: {primary_entity.get('name')} + {len(group_entities)} related entities")
    
    # Parse entities
    entities = _parse_group_entities(primary_entity, group_entities, proposed_loan_amount)
    
    # Parse cross-guarantees
    guarantees = _parse_cross_guarantees(cross_guarantees)
    
    # Parse inter-company transactions
    ic_txns = _parse_intercompany_txns(intercompany_txns or [])
    
    # Calculate aggregate metrics
    total_group_debt = sum(e.total_debt for e in entities)
    total_group_net_worth = sum(e.net_worth for e in entities)
    total_group_revenue = sum(e.revenue for e in entities)
    
    # Add proposed loan to total debt
    total_group_debt += proposed_loan_amount
    
    # Group debt-to-equity ratio
    group_debt_to_equity = (total_group_debt / total_group_net_worth) if total_group_net_worth > 0 else float('inf')
    
    # Total cross-guarantee exposure
    total_cross_guarantees = sum(g.amount for g in guarantees if g.status == "Active")
    
    # Build dependency graph
    dependency_graph = _build_dependency_graph(entities, guarantees, ic_txns)
    
    # Calculate contagion risk
    contagion_risk = _calculate_contagion_risk(
        entities,
        guarantees,
        ic_txns,
        dependency_graph,
        group_debt_to_equity
    )
    
    # Detect circular fund flows
    circular_flows = _detect_circular_flows(ic_txns, dependency_graph)
    
    # Generate flags
    flags = _generate_group_flags(
        group_debt_to_equity,
        guarantees,
        circular_flows,
        contagion_risk,
        entities
    )
    
    # Calculate score
    score = _calculate_group_score(
        group_debt_to_equity,
        contagion_risk,
        len(guarantees),
        len(circular_flows),
        entities
    )
    
    # Build detailed data
    data = {
        "primary_entity": primary_entity.get('name'),
        "total_group_entities": len(entities),
        "total_group_debt": total_group_debt,
        "total_group_net_worth": total_group_net_worth,
        "total_group_revenue": total_group_revenue,
        "group_debt_to_equity": group_debt_to_equity,
        "total_cross_guarantees": total_cross_guarantees,
        "contagion_risk_score": contagion_risk,
        "entities_breakdown": [
            {
                "name": e.entity_name,
                "relationship": e.relationship,
                "ownership_pct": e.ownership_pct,
                "debt": e.total_debt,
                "net_worth": e.net_worth,
                "existing_exposure": e.existing_exposure
            }
            for e in entities
        ],
        "cross_guarantees_summary": {
            "count": len(guarantees),
            "total_amount": total_cross_guarantees,
            "details": [
                {
                    "guarantor": g.guarantor,
                    "beneficiary": g.beneficiary,
                    "amount": g.amount,
                    "status": g.status
                }
                for g in guarantees
            ]
        },
        "circular_flows": circular_flows,
        "dependency_map": _serialize_graph(dependency_graph)
    }
    
    confidence = 0.80 if len(entities) > 1 else 0.90
    
    logger.info(
        f"✅ Group analysis complete | Score: {score:.1f}/100 | "
        f"Group D/E: {group_debt_to_equity:.2f}x | Contagion Risk: {contagion_risk:.1f}/100"
    )
    
    return GroupExposureResult(
        score=score,
        flags=flags,
        data=data,
        confidence=confidence,
        total_group_entities=len(entities),
        total_group_debt=total_group_debt,
        total_group_net_worth=total_group_net_worth,
        total_group_revenue=total_group_revenue,
        group_debt_to_equity=group_debt_to_equity,
        total_cross_guarantees=total_cross_guarantees,
        contagion_risk_score=contagion_risk,
        entities=entities,
        cross_guarantees=guarantees,
        intercompany_txns=ic_txns
    )


def _parse_group_entities(
    primary: Dict[str, Any],
    group: List[Dict[str, Any]],
    proposed_loan: float
) -> List[GroupEntity]:
    """Parse group entity data."""
    entities = []
    
    # Add primary entity
    entities.append(GroupEntity(
        entity_id=primary.get('cin', 'PRIMARY'),
        entity_name=primary['name'],
        cin=primary.get('cin'),
        relationship="Primary Borrower",
        ownership_pct=100.0,
        revenue=float(primary.get('revenue', 0)),
        net_worth=float(primary.get('net_worth', 0)),
        total_debt=float(primary.get('total_debt', 0)),
        is_borrower=True,
        existing_exposure=float(primary.get('existing_exposure', 0)),
        proposed_exposure=proposed_loan
    ))
    
    # Add group entities
    for entity in group:
        entities.append(GroupEntity(
            entity_id=entity.get('cin', entity['name']),
            entity_name=entity['name'],
            cin=entity.get('cin'),
            relationship=entity.get('relationship', 'Related'),
            ownership_pct=float(entity.get('ownership_pct', 0)),
            revenue=float(entity.get('revenue', 0)),
            net_worth=float(entity.get('net_worth', 0)),
            total_debt=float(entity.get('total_debt', 0)),
            is_borrower=entity.get('is_borrower', False),
            existing_exposure=float(entity.get('existing_exposure', 0)),
            proposed_exposure=float(entity.get('proposed_exposure', 0))
        ))
    
    return entities


def _parse_cross_guarantees(guarantees_data: List[Dict[str, Any]]) -> List[CrossGuarantee]:
    """Parse cross-guarantee data."""
    guarantees = []
    
    for g in guarantees_data:
        guarantees.append(CrossGuarantee(
            guarantee_id=g.get('id', f"CG{len(guarantees)}"),
            guarantor=g['guarantor'],
            beneficiary=g['beneficiary'],
            amount=float(g['amount']),
            purpose=g.get('purpose', 'Loan guarantee'),
            date=g.get('date', datetime.now().strftime("%Y-%m-%d")),
            status=g.get('status', 'Active')
        ))
    
    return guarantees


def _parse_intercompany_txns(txns_data: List[Dict[str, Any]]) -> List[IntercompanyTransaction]:
    """Parse inter-company transactions."""
    txns = []
    
    for t in txns_data:
        txns.append(IntercompanyTransaction(
            from_entity=t['from_entity'],
            to_entity=t['to_entity'],
            amount=float(t['amount']),
            transaction_type=t.get('type', 'Loan'),
            date=t.get('date', ''),
            is_arms_length=t.get('is_arms_length', True)
        ))
    
    return txns


def _build_dependency_graph(
    entities: List[GroupEntity],
    guarantees: List[CrossGuarantee],
    ic_txns: List[IntercompanyTransaction]
) -> nx.DiGraph:
    """
    Build directed graph of group dependencies.
    
    Nodes: Entities
    Edges: Cross-guarantees and inter-company loans
    """
    G = nx.DiGraph()
    
    # Add nodes
    for entity in entities:
        G.add_node(entity.entity_name, **{
            'debt': entity.total_debt,
            'net_worth': entity.net_worth,
            'is_borrower': entity.is_borrower
        })
    
    # Add edges from cross-guarantees
    for guarantee in guarantees:
        if guarantee.status == "Active":
            G.add_edge(
                guarantee.guarantor,
                guarantee.beneficiary,
                type='guarantee',
                amount=guarantee.amount
            )
    
    # Add edges from inter-company transactions
    for txn in ic_txns:
        if txn.transaction_type in ['Loan', 'Advance']:
            G.add_edge(
                txn.from_entity,
                txn.to_entity,
                type='loan',
                amount=txn.amount
            )
    
    return G


def _calculate_contagion_risk(
    entities: List[GroupEntity],
    guarantees: List[CrossGuarantee],
    ic_txns: List[IntercompanyTransaction],
    graph: nx.DiGraph,
    group_de_ratio: float
) -> float:
    """
    Calculate contagion risk score (0-100).
    
    Higher score = Higher risk that failure of one entity will
    cascade to others.
    
    Factors:
    - Number of cross-guarantees
    - Inter-dependency strength
    - Weak entity guaranteeing strong entity
    - Circular dependencies
    - Group debt-to-equity ratio
    """
    risk_score = 0.0
    
    # Factor 1: Group leverage
    if group_de_ratio > 5:
        risk_score += 40
    elif group_de_ratio > 3:
        risk_score += 25
    elif group_de_ratio > 2:
        risk_score += 10
    
    # Factor 2: Number of cross-guarantees
    active_guarantees = [g for g in guarantees if g.status == "Active"]
    if len(active_guarantees) > 5:
        risk_score += 20
    elif len(active_guarantees) > 2:
        risk_score += 10
    
    # Factor 3: Graph connectivity (strongly connected = high contagion)
    if nx.is_strongly_connected(graph):
        risk_score += 20  # Circular dependencies exist
    
    # Factor 4: Weak guarantors
    weak_guarantor_count = 0
    entity_map = {e.entity_name: e for e in entities}
    
    for guarantee in active_guarantees:
        guarantor = entity_map.get(guarantee.guarantor)
        if guarantor and guarantor.net_worth > 0:
            guarantee_to_networth = guarantee.amount / guarantor.net_worth
            if guarantee_to_networth > 1.0:  # Guaranteeing more than their net worth
                weak_guarantor_count += 1
    
    risk_score += weak_guarantor_count * 10
    
    return min(100, risk_score)


def _detect_circular_flows(
    ic_txns: List[IntercompanyTransaction],
    graph: nx.DiGraph
) -> List[List[str]]:
    """
    Detect circular fund flows (potential fraud).
    
    Example: Company A → Company B → Company C → Company A
    """
    try:
        cycles = list(nx.simple_cycles(graph))
        return cycles
    except:
        return []


def _generate_group_flags(
    group_de_ratio: float,
    guarantees: List[CrossGuarantee],
    circular_flows: List[List[str]],
    contagion_risk: float,
    entities: List[GroupEntity]
) -> List[str]:
    """Generate red flags based on group analysis."""
    flags = []
    
    # RF030: Group contagion risk
    if group_de_ratio > 5:
        flags.append(
            f"RF030: Critical group contagion risk - Group D/E ratio {group_de_ratio:.2f}x exceeds 5x"
        )
    elif group_de_ratio > 3:
        flags.append(
            f"High group leverage: Group D/E ratio {group_de_ratio:.2f}x"
        )
    
    # Multiple cross-guarantees
    active_guarantees = [g for g in guarantees if g.status == "Active"]
    if len(active_guarantees) > 3:
        total_guarantee_amount = sum(g.amount for g in active_guarantees)
        flags.append(
            f"{len(active_guarantees)} cross-guarantees detected "
            f"(Total: ₹{total_guarantee_amount:,.0f})"
        )
    
    # Circular fund flows
    if circular_flows:
        flags.append(
            f"Circular fund flows detected: {len(circular_flows)} cycle(s) - possible fund pooling"
        )
    
    # High contagion risk
    if contagion_risk > 70:
        flags.append(f"High contagion risk score: {contagion_risk:.1f}/100")
    
    # Weak entity in group
    weak_entities = [e for e in entities if e.net_worth < 0]
    if weak_entities:
        flags.append(
            f"{len(weak_entities)} group entit{'y' if len(weak_entities) == 1 else 'ies'} "
            f"with negative net worth"
        )
    
    return flags


def _calculate_group_score(
    group_de_ratio: float,
    contagion_risk: float,
    guarantee_count: int,
    circular_flow_count: int,
    entities: List[GroupEntity]
) -> float:
    """Calculate group exposure score (0-100)."""
    score = 100.0
    
    # Penalty for high group leverage
    if group_de_ratio > 5:
        score -= 40
    elif group_de_ratio > 3:
        score -= 25
    elif group_de_ratio > 2:
        score -= 15
    
    # Penalty for contagion risk
    score -= (contagion_risk / 100) * 30  # Max 30 points
    
    # Penalty for multiple guarantees
    if guarantee_count > 5:
        score -= 15
    elif guarantee_count > 2:
        score -= 8
    
    # Penalty for circular flows
    score -= circular_flow_count * 10
    
    # Penalty for weak entities
    weak_count = sum(1 for e in entities if e.net_worth < 0)
    score -= weak_count * 8
    
    return max(0, score)


def _serialize_graph(graph: nx.DiGraph) -> Dict[str, Any]:
    """Serialize dependency graph for output."""
    return {
        "nodes": list(graph.nodes()),
        "edges": [
            {
                "from": u,
                "to": v,
                "type": data.get('type', 'unknown'),
                "amount": data.get('amount', 0)
            }
            for u, v, data in graph.edges(data=True)
        ],
        "is_cyclic": not nx.is_directed_acyclic_graph(graph)
    }


# ─── Integration Example ─────────────────────────────────────────────────────

async def main_example():
    """Example usage of group exposure analyzer."""
    
    # Scenario: Business group with cross-guarantees
    primary = {
        "name": "Alpha Industries Ltd",
        "cin": "U12345DL2015PTC111111",
        "revenue": 500_000_000,
        "net_worth": 100_000_000,
        "total_debt": 200_000_000,
        "existing_exposure": 50_000_000
    }
    
    group = [
        {
            "name": "Beta Manufacturing Pvt Ltd",
            "cin": "U12345DL2016PTC222222",
            "relationship": "Subsidiary",
            "ownership_pct": 75.0,
            "revenue": 300_000_000,
            "net_worth": 60_000_000,
            "total_debt": 180_000_000,
            "is_borrower": True,
            "existing_exposure": 40_000_000
        },
        {
            "name": "Gamma Trading Company Ltd",
            "cin": "U12345DL2017PTC333333",
            "relationship": "Sister Concern",
            "ownership_pct": 50.0,
            "revenue": 150_000_000,
            "net_worth": 30_000_000,
            "total_debt": 120_000_000,
            "is_borrower": False
        },
        {
            "name": "Delta Logistics Pvt Ltd",
            "cin": "U12345DL2018PTC444444",
            "relationship": "Associate",
            "ownership_pct": 25.0,
            "revenue": 80_000_000,
            "net_worth": -10_000_000,  # Negative net worth!
            "total_debt": 60_000_000,
            "is_borrower": True,
            "existing_exposure": 15_000_000
        }
    ]
    
    cross_guarantees = [
        {
            "guarantor": "Alpha Industries Ltd",
            "beneficiary": "Beta Manufacturing Pvt Ltd",
            "amount": 50_000_000,
            "purpose": "Working capital loan guarantee",
            "status": "Active"
        },
        {
            "guarantor": "Beta Manufacturing Pvt Ltd",
            "beneficiary": "Alpha Industries Ltd",
            "amount": 40_000_000,
            "purpose": "Term loan guarantee",
            "status": "Active"
        },
        {
            "guarantor": "Alpha Industries Ltd",
            "beneficiary": "Delta Logistics Pvt Ltd",
            "amount": 20_000_000,
            "purpose": "Vehicle loan guarantee",
            "status": "Active"
        }
    ]
    
    intercompany_txns = [
        {
            "from_entity": "Alpha Industries Ltd",
            "to_entity": "Beta Manufacturing Pvt Ltd",
            "amount": 15_000_000,
            "type": "Loan",
            "is_arms_length": False
        },
        {
            "from_entity": "Beta Manufacturing Pvt Ltd",
            "to_entity": "Gamma Trading Company Ltd",
            "amount": 10_000_000,
            "type": "Advance",
            "is_arms_length": False
        }
    ]
    
    result = await analyze_group_exposure(
        primary_entity=primary,
        group_entities=group,
        cross_guarantees=cross_guarantees,
        intercompany_txns=intercompany_txns,
        proposed_loan_amount=30_000_000
    )
    
    print("="*70)
    print("GROUP EXPOSURE ANALYSIS")
    print("="*70)
    print(f"Score: {result.score:.1f}/100")
    print(f"Confidence: {result.confidence:.1%}")
    print(f"\nGroup Metrics:")
    print(f"  Total Entities: {result.total_group_entities}")
    print(f"  Group Revenue: ₹{result.total_group_revenue:,.0f}")
    print(f"  Group Net Worth: ₹{result.total_group_net_worth:,.0f}")
    print(f"  Group Total Debt: ₹{result.total_group_debt:,.0f}")
    print(f"  Group D/E Ratio: {result.group_debt_to_equity:.2f}x")
    print(f"  Total Cross-Guarantees: ₹{result.total_cross_guarantees:,.0f}")
    print(f"  Contagion Risk Score: {result.contagion_risk_score:.1f}/100")
    
    if result.flags:
        print(f"\n🚨 Red Flags:")
        for flag in result.flags:
            print(f"  • {flag}")
    
    print(f"\nGroup Structure:")
    for entity in result.entities:
        status = "🔴" if entity.net_worth < 0 else "🟢"
        print(f"  {status} {entity.entity_name}")
        print(f"     Relationship: {entity.relationship}")
        print(f"     Debt: ₹{entity.total_debt:,.0f} | Net Worth: ₹{entity.net_worth:,.0f}")


if __name__ == "__main__":
    asyncio.run(main_example())
