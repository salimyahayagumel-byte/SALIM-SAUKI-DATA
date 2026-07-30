from dataclasses import dataclass


@dataclass
class ScoreResult:
    score: int
    recommendation: str


class AIScoring:
    """
    AI scoring engine.
    """

    @staticmethod
    def calculate(
        liquidity_score: int,
        security_score: int,
        holders_score: int,
        whales_score: int,
        momentum_score: int,
    ) -> ScoreResult:

        total = (
            liquidity_score
            + security_score
            + holders_score
            + whales_score
            + momentum_score
        )

        total = max(0, min(total, 100))

        if total >= 90:
            recommendation = "🟢 STRONG BUY"
        elif total >= 75:
            recommendation = "🟢 BUY"
        elif total >= 60:
            recommendation = "🟡 WATCH"
        elif total >= 40:
            recommendation = "🟠 HIGH RISK"
        else:
            recommendation = "🔴 AVOID"

        return ScoreResult(
            score=total,
            recommendation=recommendation,
        )
