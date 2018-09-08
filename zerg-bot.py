import sc2
from sc2 import Race, Difficulty
from sc2.constants import HATCHERY, ZERGLING, LARVA, QUEEN, SPAWNINGPOOL, OVERLORD, EXTRACTOR, DRONE, \
    EFFECT_INJECTLARVA, RESEARCH_ZERGLINGMETABOLICBOOST, AbilityId
from sc2.player import Bot, Computer


# 100 iterations is 1 second

class ZergRushBot(sc2.BotAI):
    def __init__(self, squad_size):
        self.drone_counter = 0
        self.extractor_started = False
        self.spawning_pool_started = False
        self.moved_workers_to_gas = False
        self.moved_workers_from_gas = False
        self.queeen_started = False
        self.mboost_started = False
        self.squad_size = squad_size

    async def on_step(self, iteration):
        await self.distribute_workers()
        await self.build_workers()
        await self.build_gas_buildings()
        await self.build_supply()
        await self.build_offensive_force_buildings()
        await self.build_offensive_force()
        await self.offend()
        await self.expand()
        await self.trash_talk(iteration)
        await self.hail_mary()

        if self.vespene >= 100:
            sp = self.units(SPAWNINGPOOL).ready
            if sp.exists and self.minerals >= 100 and not self.mboost_started:
                await self.do(sp.first(RESEARCH_ZERGLINGMETABOLICBOOST))
                self.mboost_started = True

            if not self.moved_workers_from_gas:
                self.moved_workers_from_gas = True
                for drone in self.workers:
                    m = self.state.mineral_field.closer_than(10, drone.position)
                    await self.do(drone.gather(m.random, queue=True))

        if self.units(EXTRACTOR).ready.exists and not self.moved_workers_to_gas:
            self.moved_workers_to_gas = True
            extractor = self.units(EXTRACTOR).first
            for drone in self.workers.random_group_of(3):
                await self.do(drone.gather(extractor))

    async def trash_talk(self, iteration):
        if iteration == 0:
            await self.chat_send("Prepare for the battle of a lifetime!")
        if iteration == 30 * 100:
            await self.chat_send("Getting scared are we?")
        if iteration == 120 * 100:
            await self.chat_send("I see I may have found a real opponent. ;)")

    async def hail_mary(self):
        if not self.units(HATCHERY).ready.exists:
            for unit in self.workers | self.units(ZERGLING) | self.units(QUEEN):
                await self.do(unit.attack(self.enemy_start_locations[0]))
            return

    async def build_workers(self):
        if self.drone_counter < 3:
            if self.can_afford(DRONE):
                self.drone_counter += 1
                await self.do(self.units(LARVA).random.train(DRONE))

    async def build_supply(self):
        if self.supply_left < 2:
            if self.can_afford(OVERLORD) and self.units(LARVA).exists:
                await self.do(self.units(LARVA).random.train(OVERLORD))

    async def expand(self):
        if self.units(HATCHERY).amount < 2 and self.minerals > 500:
            await self.expand_now()

    async def build_offensive_force_buildings(self):
        if not self.spawning_pool_started:
            hatchery = self.units(HATCHERY).ready.first
            if self.can_afford(SPAWNINGPOOL):
                for d in range(4, 15):
                    pos = hatchery.position.to2.towards(self.game_info.map_center, d)
                    if await self.can_place(SPAWNINGPOOL, pos):
                        drone = self.workers.closest_to(pos)
                        err = await self.do(drone.build(SPAWNINGPOOL, pos))
                        if not err:
                            self.spawning_pool_started = True
                            break

    async def build_offensive_force(self):
        hatchery = self.units(HATCHERY).ready.first
        if not self.queeen_started and self.units(SPAWNINGPOOL).ready.exists:
            if self.can_afford(QUEEN):
                r = await self.do(hatchery.train(QUEEN))
                if not r:
                    self.queeen_started = True
        if self.units(SPAWNINGPOOL).ready.exists:
            larvae = self.units(LARVA)
            if larvae.exists and self.can_afford(ZERGLING):
                await self.do(larvae.random.train(ZERGLING))

        for queen in self.units(QUEEN).idle:
            abilities = await self.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                await self.do(queen(EFFECT_INJECTLARVA, hatchery))

    async def build_gas_buildings(self):
        if not self.extractor_started:
            if self.can_afford(EXTRACTOR):
                drone = self.workers.random
                target = self.state.vespene_geyser.closest_to(drone.position)
                err = await self.do(drone.build(EXTRACTOR, target))
                if not err:
                    self.extractor_started = True

    async def offend(self):
        target = self.known_enemy_structures.random_or(self.enemy_start_locations[0]).position
        if len(self.units(ZERGLING).filter(lambda my_unit: not my_unit.is_attacking)) > 6:
            for zl in self.units(ZERGLING):
                await self.do(zl.attack(target))


def main():
    sc2.run_game(sc2.maps.get("Simple64"), [
        Bot(Race.Zerg, ZergRushBot(6)),
        Computer(Race.Protoss, Difficulty.VeryHard)
    ], realtime=False, save_replay_as="ZvP.SC2Replay")


if __name__ == '__main__':
    main()
