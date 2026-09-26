"""Battle-only rules extracted unchanged from upstream Level; no campaign/UI state machine."""
import random
import pygame as pg
from . import constants as c
from .entities import props


class CombatRules:
    def setupCars(self):
        self.cars = []
        for i in range(self.map_y_len):
            y = self.map.getMapGridPos(0, i)[1]
            self.cars.append(props.Car(-45, y + 20, i))

    def checkZombieCollisions(self):
        for i in range(self.map_y_len):
            for zombie in self.zombie_groups[i]:
                if zombie.name == c.ZOMBONI:
                    continue
                if zombie.name in {c.POLE_VAULTING_ZOMBIE} and (not zombie.jumped):
                    collided_func = pg.sprite.collide_rect_ratio(0.6)
                else:
                    collided_func = pg.sprite.collide_mask
                if zombie.state != c.WALK:
                    # 非啃咬时不用刷新
                    if zombie.state != c.ATTACK:
                        continue
                    # 没有新的植物种下时不用刷新
                    if not self.new_plant_and_positon:
                        continue
                    # 被攻击对象是植物时才可能刷新
                    if zombie.prey_is_plant:
                        # 新植物种在被攻击植物同一格时才可能刷新
                        if (
                            zombie.prey_map_x,
                            zombie.prey_map_y,
                        ) == self.new_plant_and_positon[1]:
                            # 如果被攻击植物是睡莲和花盆，同一格种了植物必然刷新
                            # 如果被攻击植物不是睡莲和花盆，同一格种了南瓜头才刷新
                            if (zombie.prey.name not in {c.LILYPAD, "花盆（未实现）"}) and (
                                self.new_plant_and_positon[0] != c.PUMPKINHEAD
                            ):
                                continue
                        else:
                            continue
                    else:
                        continue
                if zombie.can_swim and (not zombie.swimming):
                    continue

                # 以下代码为了实现各个功能，较为凌乱
                attackable_common_plants = []
                attackable_backup_plants = []
                # 利用更加精细的循环判断啃咬优先顺序
                for plant in self.plant_groups[i]:
                    if collided_func(plant, zombie):
                        # 优先攻击南瓜头
                        if plant.name == c.PUMPKINHEAD:
                            target_plant = plant
                            break
                        # 衬底植物情形
                        elif plant.name in {c.LILYPAD, "花盆（未实现）"}:
                            attackable_backup_plants.append(plant)
                        # 一般植物情形
                        # 同时也忽略了不可啃食对象
                        elif plant.name not in c.CAN_SKIP_ZOMBIE_COLLISION_CHECK:
                            attackable_common_plants.append(plant)
                        # 在生效状态下忽略啃食碰撞但其他状况下不能忽略的情形
                        elif plant.name in c.SKIP_ZOMBIE_COLLISION_CHECK_WHEN_WORKING:
                            if not plant.start_boom:
                                attackable_common_plants.append(plant)
                else:
                    if attackable_common_plants:
                        # 默认为最右侧的一个植物
                        target_plant = max(attackable_common_plants, key=lambda i: i.rect.x)
                        map_x, map_y = self.map.getMapIndex(
                            target_plant.rect.centerx,
                            target_plant.rect.centery,
                        )
                        if self.map.isValid(map_x, map_y):
                            if c.PUMPKINHEAD in self.map.map[map_y][map_x][c.MAP_PLANT]:
                                for actual_target_plant in self.plant_groups[i]:
                                    # 检测同一格的其他植物
                                    if self.map.getMapIndex(
                                        actual_target_plant.rect.centerx,
                                        actual_target_plant.rect.bottom,
                                    ) == (map_x, map_y):
                                        if actual_target_plant.name == c.PUMPKINHEAD:
                                            target_plant = actual_target_plant
                                            break
                    elif attackable_backup_plants:
                        target_plant = max(attackable_backup_plants, key=lambda i: i.rect.x)
                        map_x, map_y = self.map.getMapIndex(
                            target_plant.rect.centerx,
                            target_plant.rect.centery,
                        )
                        if len(self.map.map[map_y][map_x][c.MAP_PLANT]) >= 2:
                            for actual_target_plant in self.plant_groups[i]:
                                # 检测同一格的其他植物
                                if self.map.getMapIndex(
                                    actual_target_plant.rect.centerx,
                                    actual_target_plant.rect.bottom,
                                ) == (map_x, map_y):
                                    if actual_target_plant.name == c.PUMPKINHEAD:
                                        target_plant = actual_target_plant
                                        break
                                    elif actual_target_plant.name not in {
                                        c.LILYPAD,
                                        "花盆（未实现）",
                                    }:
                                        attackable_common_plants.append(actual_target_plant)
                            else:
                                if attackable_common_plants:
                                    target_plant = attackable_common_plants[-1]
                    else:
                        target_plant = None

                if target_plant:
                    (
                        zombie.prey_map_x,
                        zombie.prey_map_y,
                    ) = self.map.getMapIndex(target_plant.rect.centerx, target_plant.rect.centery)
                    # 撑杆跳的特殊情况
                    if zombie.name in {c.POLE_VAULTING_ZOMBIE} and (not zombie.jumped):
                        if target_plant.name == c.GIANTWALLNUT:
                            zombie.health = 0
                            c.SOUND_BOWLING_IMPACT.play()
                        elif not zombie.jumping:
                            zombie.jump_map_x = min(self.map_x_len - 1, zombie.prey_map_x)
                            zombie.jump_map_y = min(self.map_y_len - 1, zombie.prey_map_y)
                            jump_x = target_plant.rect.x - c.GRID_X_SIZE * 0.6
                            if (
                                c.TALLNUT
                                in self.map.map[zombie.jump_map_y][zombie.jump_map_x][c.MAP_PLANT]
                            ):
                                zombie.setJump(False, jump_x)
                            else:
                                zombie.setJump(True, jump_x)
                        else:
                            if (
                                c.TALLNUT
                                in self.map.map[zombie.jump_map_y][zombie.jump_map_x][c.MAP_PLANT]
                            ):
                                zombie.setJump(False, zombie.jump_x)
                            else:
                                zombie.setJump(True, zombie.jump_x)
                        continue

                    if target_plant.name == c.WALLNUTBOWLING:
                        if target_plant.canHit(i):
                            # target_plant.vel_y不为0，有纵向速度，表明已经发生过碰撞，对铁门秒杀（这里实现为忽略二类防具攻击）
                            if target_plant.vel_y and zombie.name == c.SCREEN_DOOR_ZOMBIE:
                                zombie.setDamage(
                                    c.WALLNUT_BOWLING_DAMAGE,
                                    damage_type=c.ZOMBIE_COMMON_DAMAGE,
                                )
                            else:
                                zombie.setDamage(
                                    c.WALLNUT_BOWLING_DAMAGE,
                                    damage_type=c.ZOMBIE_WALLNUT_BOWLING_DANMAGE,
                                )
                            target_plant.changeDirection(i)
                            # 播放撞击音效
                            c.SOUND_BOWLING_IMPACT.play()
                    elif target_plant.name == c.REDWALLNUTBOWLING:
                        if target_plant.state == c.IDLE:
                            target_plant.setAttack()
                    elif target_plant.name == c.GIANTWALLNUT:
                        zombie.health = 0
                        c.SOUND_BOWLING_IMPACT.play()
                    elif zombie.target_y_change:
                        # 大蒜作用正在生效的僵尸不进行传递
                        continue
                    elif target_plant.name == c.GARLIC:
                        zombie.setAttack(target_plant)
                        # 向吃过大蒜的僵尸传入level
                        zombie.level = self
                        zombie.to_change_group = True
                        zombie.map_y = i
                        if i == 0:
                            _move = 1
                        elif i == self.map_y_len - 1:
                            _move = -1
                        else:
                            _move = random.randint(0, 1) * 2 - 1
                            if (
                                self.map.map[i][0][c.MAP_PLOT_TYPE]
                                != self.map.map[i + _move][0][c.MAP_PLOT_TYPE]
                            ):
                                _move = -(_move)
                        zombie.target_map_y = i + _move
                        zombie.target_y_change = _move * self.map.grid_height_size
                    else:
                        zombie.setAttack(target_plant)

            for hypno_zombie in self.hypno_zombie_groups[i]:
                if hypno_zombie.health <= 0:
                    continue
                collided_func = pg.sprite.collide_mask
                zombie_list = pg.sprite.spritecollide(
                    hypno_zombie, self.zombie_groups[i], False, collided_func
                )
                for zombie in zombie_list:
                    if zombie.state == c.DIE:
                        continue
                    # 正常僵尸攻击被魅惑的僵尸
                    if zombie.state == c.WALK:
                        zombie.setAttack(hypno_zombie, False)
                    # 被魅惑的僵尸攻击正常僵尸
                    if hypno_zombie.state == c.WALK:
                        hypno_zombie.setAttack(zombie, False)

        else:
            self.new_plant_and_positon = None  # 生效后需要解除刷新设置

    def boomZombies(self, x, map_y, y_range, x_range, effect=None):
        for i in range(self.map_y_len):
            if abs(i - map_y) > y_range:
                continue
            for zombie in self.zombie_groups[i]:
                if (abs(zombie.rect.centerx - x) <= x_range) or (
                    (zombie.rect.right - (x - x_range) > 20)
                    or (zombie.rect.right - (x - x_range)) / zombie.rect.width > 0.2,
                    ((x + x_range) - zombie.rect.left > 20)
                    or ((x + x_range) - zombie.rect.left) / zombie.rect.width > 0.2,
                )[
                    zombie.rect.x > x
                ]:  # 这代码不太好懂，后面是一个判断僵尸在左还是在右，前面是一个元组，[0]是在左边的情况，[1]是在右边的情况
                    if effect == c.BULLET_EFFECT_UNICE:
                        zombie.ice_slow_ratio = 1
                    zombie.setDamage(1800, damage_type=c.ZOMBIE_ASH_DAMAGE)
                    if zombie.health <= 0:
                        zombie.setBoomDie()

    def freezeZombies(self, plant):
        # 播放冻结音效
        c.SOUND_FREEZE.play()

        for i in range(self.map_y_len):
            for zombie in self.zombie_groups[i]:
                zombie.setFreeze(plant.trap_frames[0])
                zombie.setDamage(20, damage_type=c.ZOMBIE_RANGE_DAMAGE)  # 寒冰菇还有全场20的伤害

    def checkPlant(self, target_plant, i):
        zombie_len = len(self.zombie_groups[i])
        # 不用检查攻击状况的情况
        if not target_plant.attack_check:
            pass
        elif target_plant.name == c.THREEPEASHOOTER:
            if target_plant.state == c.IDLE:
                if zombie_len > 0:
                    target_plant.setAttack()
                elif (i - 1) >= 0 and len(self.zombie_groups[i - 1]) > 0:
                    target_plant.setAttack()
                elif (i + 1) < self.map_y_len and len(self.zombie_groups[i + 1]) > 0:
                    target_plant.setAttack()
            elif target_plant.state == c.ATTACK:
                if zombie_len > 0:
                    pass
                elif (i - 1) >= 0 and len(self.zombie_groups[i - 1]) > 0:
                    pass
                elif (i + 1) < self.map_y_len and len(self.zombie_groups[i + 1]) > 0:
                    pass
                else:
                    target_plant.setIdle()
        elif target_plant.name == c.CHOMPER:
            for zombie in self.zombie_groups[i]:
                if target_plant.canAttack(zombie):
                    target_plant.setAttack(zombie, self.zombie_groups[i])
                    break
        elif target_plant.name == c.POTATOMINE:
            for zombie in self.zombie_groups[i]:
                if target_plant.canAttack(zombie):
                    target_plant.setAttack()
                    break
            if target_plant.start_boom and (not target_plant.boomed):
                for zombie in self.zombie_groups[i]:
                    # 双判断：发生碰撞或在攻击范围内
                    if (pg.sprite.collide_mask(zombie, target_plant)) or (
                        abs(zombie.rect.centerx - target_plant.rect.centerx)
                        <= target_plant.explode_x_range
                    ):
                        zombie.setDamage(1800, damage_type=c.ZOMBIE_RANGE_DAMAGE)
                target_plant.boomed = True
        elif target_plant.name == c.SQUASH:
            for zombie in self.zombie_groups[i]:
                if target_plant.canAttack(zombie):
                    target_plant.setAttack(zombie, self.zombie_groups[i])
                    break
        elif target_plant.name == c.SPIKEWEED:
            can_attack = False
            for zombie in self.zombie_groups[i]:
                if target_plant.canAttack(zombie):
                    can_attack = True
                    break
            if target_plant.state == c.IDLE and can_attack:
                target_plant.setAttack(self.zombie_groups[i])
            elif target_plant.state == c.ATTACK and not can_attack:
                target_plant.setIdle()
        elif target_plant.name == c.SCAREDYSHROOM:
            need_cry = False
            can_attack = False
            for zombie in self.zombie_groups[i]:
                if target_plant.needCry(zombie):
                    need_cry = True
                    break
                elif target_plant.canAttack(zombie):
                    can_attack = True
            if need_cry:
                if target_plant.state != c.CRY:
                    target_plant.setCry()
            elif can_attack:
                if target_plant.state != c.ATTACK:
                    target_plant.setAttack()
            elif target_plant.state != c.IDLE:
                target_plant.setIdle()
        elif target_plant.name == c.STARFRUIT:
            can_attack = False
            for zombie_group in self.zombie_groups:  # 遍历循环所有僵尸
                for zombie in zombie_group:
                    if target_plant.canAttack(zombie):
                        can_attack = True
                        break
            if target_plant.state == c.IDLE and can_attack:
                target_plant.setAttack()
            elif target_plant.state == c.ATTACK and not can_attack:
                target_plant.setIdle()
        elif target_plant.name == c.TANGLEKLEP:
            for zombie in self.zombie_groups[i]:
                if target_plant.canAttack(zombie):
                    target_plant.setAttack(zombie, self.zombie_groups[i])
                    break
        # 灰烬植物与寒冰菇
        elif target_plant.name in c.ASH_PLANTS_AND_ICESHROOM:
            if target_plant.start_boom and (not target_plant.boomed):
                # 这样分成两层是因为场上灰烬植物肯定少，一个一个判断代价高，先笼统判断灰烬即可
                if target_plant.name in {c.REDWALLNUTBOWLING, c.CHERRYBOMB}:
                    self.boomZombies(
                        target_plant.rect.centerx,
                        i,
                        target_plant.explode_y_range,
                        target_plant.explode_x_range,
                    )
                elif target_plant.name == c.DOOMSHROOM:
                    x, y = target_plant.original_x, target_plant.original_y
                    map_x, map_y = self.map.getMapIndex(x, y)
                    self.boomZombies(
                        target_plant.rect.centerx,
                        i,
                        target_plant.explode_y_range,
                        target_plant.explode_x_range,
                    )
                    for item in self.plant_groups[map_y]:
                        checkMapX, _ = self.map.getMapIndex(item.rect.centerx, item.rect.bottom)
                        if map_x == checkMapX:
                            item.health = 0
                    # 为了防止坑显示在蘑菇云前面，这里先不生成坑，仅填位置
                    self.map.map[map_y][map_x][c.MAP_PLANT].add(c.HOLE)
                elif target_plant.name == c.JALAPENO:
                    self.boomZombies(
                        target_plant.rect.centerx,
                        i,
                        target_plant.explode_y_range,
                        target_plant.explode_x_range,
                        effect=c.BULLET_EFFECT_UNICE,
                    )
                    # 消除冰道
                    for item in self.plant_groups[i]:
                        if item.name == c.ICEFROZENPLOT:
                            item.health = 0
                elif target_plant.name == c.ICESHROOM:
                    self.freezeZombies(target_plant)
                target_plant.boomed = True
        else:
            can_attack = False
            if zombie_len > 0:
                for zombie in self.zombie_groups[i]:
                    if target_plant.canAttack(zombie):
                        can_attack = True
                        break
            if target_plant.state == c.IDLE and can_attack:
                target_plant.setAttack()
            elif target_plant.state == c.ATTACK and (not can_attack):
                target_plant.setIdle()

    def checkPlants(self):
        for i in range(self.map_y_len):
            for plant in self.plant_groups[i]:
                if plant.state != c.SLEEP:
                    self.checkPlant(plant, i)
                if plant.health <= 0:
                    self.killPlant(plant)

    def checkLose(self):
        for i in range(self.map_y_len):
            for zombie in self.zombie_groups[i]:
                if zombie.rect.right < -20 and (not zombie.losthead) and (zombie.state != c.DIE):
                    return True
        return False
