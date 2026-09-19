from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Dict, Optional


class GemIntelligence:
    """Evidence-aware V9 GEM calling layer.

    This layer never invents holder, wallet, creator, or liquidity-history
    data. It uses fields supplied by upstream providers when available and
    otherwise assigns a neutral/limited-evidence score.

    The goal is to prioritize early, liquid, active tokens while penalizing
    abnormal activity and unstable conditions.
    """

    MIN_MC = 10_000.0
    MAX_MC = 5_000_000.0

    def __init__(self, confirmation_scans: int = 3, history_size: int = 8):
        self.confirmation_scans = max(1, int(confirmation_scans))
        self.history_size = max(3, int(history_size))
        self._history = defaultdict(lambda: deque(maxlen=self.history_size))

    @staticmethod
    def num(v: Any, default: float = 0.0) -> float:
        try:
            if v is None:
                return default
            return float(v)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, v))

    def _key(self, token: Dict[str, Any]) -> str:
        return f"{str(token.get('chain','')).lower()}:{str(token.get('address','')).lower()}"

    def _pair_age_minutes(self, token: Dict[str, Any]) -> Optional[float]:
        created = self.num(token.get("pair_created"), 0)
        if not created:
            return None
        # DexScreener uses milliseconds.
        if created > 10_000_000_000:
            created /= 1000.0
        age = (time.time() - created) / 60.0
        return max(0.0, age)

    def _metric(self, token: Dict[str, Any], *names: str) -> Optional[float]:
        for name in names:
            if name in token and token.get(name) is not None:
                return self.num(token.get(name))
        return None

    def analyze(self, token: Dict[str, Any]) -> Dict[str, Any]:
        mc = self.num(token.get("marketcap", token.get("market_cap")))
        liq = self.num(token.get("liquidity"))
        vol = self.num(token.get("volume24h", token.get("volume_24h")))
        buys = self.num(token.get("buys24h"))
        sells = self.num(token.get("sells24h"))
        txns = self.num(token.get("total_txns"), buys + sells)
        buy_ratio = self.num(token.get("buy_ratio"))
        if buy_ratio <= 0 and txns > 0:
            buy_ratio = buys / txns

        liq_mc = liq / mc if mc > 0 else 0.0
        vol_mc = vol / mc if mc > 0 else 0.0
        age = self._pair_age_minutes(token)

        p5 = self._metric(token, "price_change_5m")
        p15 = self._metric(token, "price_change_15m")
        p1h = self._metric(token, "price_change_1h")
        v5 = self._metric(token, "volume_5m")
        v1h = self._metric(token, "volume_1h")
        b5 = self._metric(token, "buys5m")
        s5 = self._metric(token, "sells5m")

        # 1) Early entry: young pool + small cap + healthy liquidity + fresh activity.
        early = 45.0
        early_reasons = []
        if age is not None:
            if age <= 30:
                early += 35
                early_reasons.append("POOL <30M")
            elif age <= 120:
                early += 25
                early_reasons.append("POOL <2H")
            elif age <= 360:
                early += 15
                early_reasons.append("POOL <6H")
            elif age <= 1440:
                early += 7
        else:
            early -= 5
        if 10_000 <= mc <= 500_000:
            early += 10
        if liq_mc >= 0.15:
            early += 8
        elif liq_mc >= 0.08:
            early += 4
        if txns >= 50:
            early += 4
        early = self.clamp(early)

        # 2) Liquidity quality: size + liq/MC + optional stability/growth evidence.
        liquidity = 35.0
        if liq >= 250_000: liquidity += 30
        elif liq >= 100_000: liquidity += 25
        elif liq >= 50_000: liquidity += 20
        elif liq >= 25_000: liquidity += 14
        elif liq >= 10_000: liquidity += 8
        else: liquidity -= 20
        if liq_mc >= .30: liquidity += 25
        elif liq_mc >= .20: liquidity += 20
        elif liq_mc >= .10: liquidity += 12
        elif liq_mc >= .05: liquidity += 5
        else: liquidity -= 8

        liq_growth = self._metric(token, "liquidity_growth_5m", "liquidity_change_5m")
        liq_removal = self._metric(token, "liquidity_removal_pct", "liquidity_removed_pct")
        if liq_growth is not None:
            liquidity += max(-10, min(10, liq_growth / 5))
        if liq_removal is not None and liq_removal >= 20:
            liquidity -= 35
        liquidity = self.clamp(liquidity)

        # 3) Volume quality and acceleration.
        volume_quality = 40.0
        if .05 <= vol_mc <= 5:
            volume_quality += 25
        elif vol_mc < .05:
            volume_quality -= 15
        elif vol_mc > 15:
            volume_quality -= 25
        elif vol_mc > 10:
            volume_quality -= 15
        if buy_ratio >= .65: volume_quality += 15
        elif buy_ratio >= .55: volume_quality += 9
        elif buy_ratio < .50: volume_quality -= 15
        if txns >= 250: volume_quality += 8
        elif txns >= 100: volume_quality += 5

        volume_acceleration = None
        if v5 is not None and v1h is not None and v1h > 0:
            # Compare 5m pace against the average 5m slice of the 1h volume.
            volume_acceleration = (v5 / (v1h / 12.0))
            if volume_acceleration >= 2.5: volume_quality += 15
            elif volume_acceleration >= 1.5: volume_quality += 9
            elif volume_acceleration < .5: volume_quality -= 8
        else:
            volume_acceleration = None

        if b5 is not None and s5 is not None and (b5 + s5) > 0:
            buy_ratio_5m = b5 / (b5 + s5)
            if buy_ratio_5m >= .65: volume_quality += 8
            elif buy_ratio_5m < .45: volume_quality -= 10
        else:
            buy_ratio_5m = None
        volume_quality = self.clamp(volume_quality)

        # 4) Momentum.
        momentum = 40.0
        if p5 is not None:
            if p5 >= 15: momentum += 20
            elif p5 >= 7: momentum += 14
            elif p5 >= 2: momentum += 8
            elif p5 < -10: momentum -= 15
        if p15 is not None:
            if p15 >= 20: momentum += 15
            elif p15 >= 8: momentum += 10
            elif p15 >= 0: momentum += 5
            elif p15 < -15: momentum -= 10
        if p1h is not None:
            if p1h >= 30: momentum += 15
            elif p1h >= 10: momentum += 9
            elif p1h < -20: momentum -= 15
        if p5 is None and p15 is None and p1h is None:
            # Existing 24h momentum is still useful, but less responsive.
            p24 = self.num(token.get("price_change_24h"))
            momentum += 10 if p24 >= 5 else (4 if p24 >= 0 else -8)
        momentum = self.clamp(momentum)

        # 5) Holder intelligence: only real provider fields count.
        holders = self._metric(token, "holders", "holder_count")
        holder_growth = self._metric(token, "holder_growth_1h", "holder_growth_24h")
        holder_concentration = self._metric(token, "top10_holder_pct", "top_holder_concentration")
        holder_score = 50.0
        holder_evidence = False
        if holders is not None:
            holder_evidence = True
            if holders >= 1000: holder_score += 15
            elif holders >= 500: holder_score += 10
            elif holders >= 100: holder_score += 5
            elif holders < 30: holder_score -= 15
        if holder_growth is not None:
            holder_evidence = True
            holder_score += max(-15, min(20, holder_growth))
        if holder_concentration is not None:
            holder_evidence = True
            if holder_concentration >= 60: holder_score -= 30
            elif holder_concentration >= 45: holder_score -= 18
            elif holder_concentration >= 30: holder_score -= 8
            elif holder_concentration <= 20: holder_score += 10
        holder_score = self.clamp(holder_score)

        # 6) Smart money: evidence-aware, never inferred from aggregate volume.
        smart_score = 50.0
        smart_evidence = False
        smart_count = self._metric(token, "smart_money_wallets", "strong_wallets_entered")
        smart_buy_usd = self._metric(token, "smart_money_buy_usd")
        smart_sell_usd = self._metric(token, "smart_money_sell_usd")
        if smart_count is not None:
            smart_evidence = True
            if smart_count >= 5: smart_score += 25
            elif smart_count >= 3: smart_score += 18
            elif smart_count >= 1: smart_score += 8
        if smart_buy_usd is not None or smart_sell_usd is not None:
            smart_evidence = True
            ratio = smart_buy_usd / max(smart_sell_usd, 1.0) if smart_buy_usd is not None else 0
            if ratio >= 3: smart_score += 20
            elif ratio >= 1.5: smart_score += 10
            elif ratio < .7: smart_score -= 15
        smart_score = self.clamp(smart_score)

        # 7) Creator risk: only explicit creator/provider evidence is used.
        creator_score = 70.0
        creator_risk = self._metric(token, "creator_risk_score", "deployer_risk_score")
        creator_sell = self._metric(token, "creator_sell_pct", "creator_sold_pct")
        creator_history = token.get("creator_history")
        if creator_risk is not None:
            creator_score = self.clamp(100 - creator_risk)
        if creator_sell is not None:
            creator_score -= min(50, creator_sell)
        if isinstance(creator_history, dict):
            launches = self.num(creator_history.get("previous_launches"))
            rugs = self.num(creator_history.get("rug_count"))
            if rugs > 0: creator_score -= min(60, rugs * 20)
            elif launches >= 2: creator_score += 5
        creator_score = self.clamp(creator_score)

        # 8) Security. Existing security engine remains the authority.
        security = self.num(token.get("security_score"))
        if token.get("security_should_pass") is False:
            security = min(security, 25)
        if token.get("honeypot_detected") is True:
            security = 0

        # 9) False-signal filter.
        false_penalty = 0.0
        false_flags = []
        if vol_mc >= 25:
            false_penalty += 35; false_flags.append("EXTREME VOLUME/MC")
        elif vol_mc >= 15:
            false_penalty += 20; false_flags.append("ABNORMAL VOLUME/MC")
        if buy_ratio >= .90 and txns < 100:
            false_penalty += 12; false_flags.append("THIN EXTREME BUY RATIO")
        if holder_concentration is not None and holder_concentration >= 60:
            false_penalty += 20; false_flags.append("HIGH HOLDER CONCENTRATION")
        if liq_removal is not None and liq_removal >= 20:
            false_penalty += 25; false_flags.append("LIQUIDITY REMOVAL")
        if creator_sell is not None and creator_sell >= 15:
            false_penalty += 20; false_flags.append("CREATOR SELLING")
        if p5 is not None and p1h is not None and p5 < -12 and p1h > 25:
            false_penalty += 10; false_flags.append("SUDDEN MOMENTUM REVERSAL")
        false_penalty = min(60, false_penalty)

        # Weighted GEM Score 2.0.
        gem = (
            security * .20
            + liquidity * .15
            + momentum * .15
            + smart_score * .10
            + holder_score * .10
            + creator_score * .10
            + volume_quality * .10
            + early * .10
            - false_penalty
        )
        gem = int(round(self.clamp(gem)))

        # Confidence is lower when key intelligence sources are absent.
        evidence = 0
        for present in (age is not None, p5 is not None or p15 is not None,
                        holder_evidence, smart_evidence, creator_risk is not None or isinstance(creator_history, dict)):
            evidence += int(bool(present))
        confidence = int(round(self.clamp(55 + evidence * 9 + security * .12 - false_penalty * .25)))

        # Three-scan confirmation. A token must stay strong and not trigger
        # a hard safety block across consecutive scans.
        key = self._key(token)
        snapshot = {
            "gem": gem,
            "security": security,
            "momentum": momentum,
            "liq": liquidity,
            "volume": volume_quality,
            "false_penalty": false_penalty,
            "ts": time.time(),
        }
        hist = self._history[key]
        hist.append(snapshot)

        strong = gem >= 70 and security >= 70 and false_penalty < 25
        consecutive = 0
        for item in reversed(hist):
            if item["gem"] >= 65 and item["security"] >= 70 and item["false_penalty"] < 25:
                consecutive += 1
            else:
                break
        confirmed = strong and consecutive >= self.confirmation_scans

        if confirmed:
            stage = "CONFIRMED GEM"
        elif consecutive >= 2:
            stage = "MOMENTUM CONFIRMING"
        elif consecutive >= 1:
            stage = "CANDIDATE"
        else:
            stage = "WATCH"

        hard_block = security < 70 or token.get("honeypot_detected") is True
        if hard_block:
            confirmed = False
            stage = "SECURITY BLOCK"

        return {
            "gem_score_2": gem,
            "confidence_2": confidence,
            "security_score_2": int(round(security)),
            "liquidity_quality_score": int(round(liquidity)),
            "momentum_score": int(round(momentum)),
            "smart_money_score": int(round(smart_score)),
            "holder_score": int(round(holder_score)),
            "creator_score": int(round(creator_score)),
            "volume_quality_score": int(round(volume_quality)),
            "early_entry_score": int(round(early)),
            "false_signal_penalty": int(round(false_penalty)),
            "false_signal_flags": false_flags,
            "pool_age_minutes": age,
            "liquidity_mc_ratio": liq_mc,
            "volume_mc_ratio": vol_mc,
            "volume_acceleration": volume_acceleration,
            "buy_ratio_5m": buy_ratio_5m,
            "confirmation_count": min(consecutive, self.confirmation_scans),
            "confirmation_required": self.confirmation_scans,
            "confirmed_gem": confirmed,
            "signal_stage": stage,
            "evidence_count": evidence,
            "reasons": early_reasons,
        }
