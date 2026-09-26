"""Single authoritative resource/cooldown ledger, independent of UI."""
from game.catalog import card_defaults


class ResourceLedger:
    def __init__(self, config):
        self.sun = config.initial_sun
        self.cooldowns = dict.fromkeys(config.enabled_plants, 0)
        self.prices, self.cooldown_lengths = {}, {}
        for name in config.enabled_plants:
            price, cooldown = card_defaults(name)
            overrides = config.plant_overrides.get(name, {})
            self.prices[name] = overrides.get("cost", price)
            self.cooldown_lengths[name] = overrides.get("cooldown_ms", cooldown)

    def check(self, name, now_ms):
        if self.sun < self.prices[name]:
            return "INSUFFICIENT_SUN"
        if now_ms < self.cooldowns[name]:
            return "COOLDOWN"
        return None

    def spend(self, name, now_ms):
        # Called only after validation and successful entity construction/placement.
        self.sun -= self.prices[name]
        self.cooldowns[name] = now_ms + self.cooldown_lengths[name]
        return self.prices[name]

    def credit(self, amount):
        actual = min(amount, 9990 - self.sun)
        self.sun += actual
        return actual
