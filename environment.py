import collections
import numpy as np
import torch
import pandas as pd
import random
from local_update import cache_hit_ratio, cache_hit_ratio2
import math

class CacheEnv(object):

    def __init__(self, popular_content,cache_size):
        self.cache_size=cache_size
        self.popular_content = popular_content       # 推荐的电影
        self.action_bound = [0,1]
        self.reward = np.zeros(shape=1, dtype=float)

        #cache list
        if len(self.popular_content) < self.cache_size:
            self.state = self.popular_content

        if len(self.popular_content) >= self.cache_size:
            self.state = random.sample(list(self.popular_content), self.cache_size) # 状态是随机采样的100个推荐电影

        state1 = []
        for i in range(len(self.popular_content)):
            # 按照内容流行度进行排序
            if self.popular_content[i] in self.state:
                state1.append(self.popular_content[i])
        self.state = state1

        self.last_content=[]        # 剩下的电影
        for i in range(len(self.popular_content)):
            if self.popular_content[i] not in self.state:
                self.last_content.append(self.popular_content[i])
        print('self.last_content',len(self.last_content))
        print('self.cache_size',self.cache_size)

        if len(self.last_content)<self.cache_size:
            self.state2 = []
            for i in range(len(self.last_content)):
                if self.last_content[i] not in self.state:
                    self.state2.append(self.last_content[i])

        if len(self.last_content)>=self.cache_size:
            self.state2 = random.sample(list(self.last_content), self.cache_size)

        # 2个RSU分别存放推荐的电影,第一个放前100个，后一个放后100个
        self.init_state = self.state.copy()
        self.init_cash2 = self.state2.copy()
        self.init_last_content = self.last_content.copy()

        # Phase 4c: sort state2 by popularity (state is already sorted;
        # original code left state2 as an unsorted random sample).
        # Then build last_content2 — items not cached by RSU2 — which
        # gives RSU2 an independent replacement pool for its own agent.
        self.state2 = [item for item in self.popular_content
                       if item in self.state2]
        self.init_cash2 = self.state2.copy()          # overwrite with sorted

        self.last_content2 = [item for item in self.popular_content
                               if item not in self.state2]
        self.init_last_content2 = self.last_content2.copy()

    def step(self, action, request_dataset, v2i_rate,v2i_rate_mbs, vehicle_epoch, vehicle_request_num, print_step):
        action = np.clip(action, *self.action_bound)

        if action == 1:

            # Phase 4a: FL-guided eviction.
            # last_content is ordered by FL popularity (most popular first).
            # Select top-N uncached items rather than random candidates.
            # Fix: use a for-loop so all N items are actually replaced
            # (original code used `if count < 5` which ran exactly once).
            n_replace = min(5, len(self.last_content))
            replace_content = self.last_content[:n_replace]
            for count in range(n_replace):
                self.state[-count - 1] = replace_content[count]

            state1 = []
            for i in range(len(self.popular_content)):
                # 按照内容流行度进行排序
                if self.popular_content[i] in self.state:
                    state1.append(self.popular_content[i])
            self.state = state1

            last_content=[]
            for i in range(len(self.popular_content)):
                if self.popular_content[i] not in self.state:
                    last_content.append(self.popular_content[i])
            self.last_content=last_content

            if len(self.last_content)<=self.cache_size:
                self.state2 = self.last_content
            if len(self.last_content)>self.cache_size:
                self.state2 = random.sample(list(self.last_content), self.cache_size)

        all_vehicle_request_num = 0
        for i in range(len(vehicle_epoch)):
            all_vehicle_request_num += vehicle_request_num[vehicle_epoch[i]]
        #print('=================================all_vehicle_request_num', all_vehicle_request_num,'================================')
        cache_efficiency = cache_hit_ratio(request_dataset, self.state,
                                           all_vehicle_request_num)
        cache_efficiency2 = cache_hit_ratio2(request_dataset, self.state2 , self.state,
                                           all_vehicle_request_num)
        cache_efficiency = cache_efficiency/100
        cache_efficiency2 = cache_efficiency2/100

        reward=0
        request_delay=0
        for i in range(len(vehicle_epoch)):
            vehicle_idx=vehicle_epoch[i]
            reward += cache_efficiency * math.exp(-0.0001 * 8000000 / v2i_rate[vehicle_idx]) * vehicle_request_num[vehicle_idx]
            reward += cache_efficiency2 * math.exp(-0.0001 * 8000000 / v2i_rate[vehicle_idx]
                                                    -0.4 * 8000000 / 15000000) * vehicle_request_num[vehicle_idx]
            reward += (1-cache_efficiency-cache_efficiency2)\
                                        * math.exp(- 0.5999 * 8000000 / (v2i_rate[vehicle_idx]/2))* vehicle_request_num[vehicle_idx]

            request_delay += cache_efficiency * vehicle_request_num[vehicle_idx] / v2i_rate[vehicle_idx]*800


            #print(i,'local rsu delay', vehicle_request_num[vehicle_idx] / v2i_rate[vehicle_idx]*100000)
            request_delay += cache_efficiency2 * (
                    vehicle_request_num[vehicle_idx] / v2i_rate[vehicle_idx]+vehicle_request_num[vehicle_idx] / 15000000) *800
            #print(i,'neighbouring rsu delay',(vehicle_request_num[vehicle_idx] / v2i_rate[vehicle_idx]+vehicle_request_num[vehicle_idx] / 15000000) *100000)
            request_delay +=(1-cache_efficiency-cache_efficiency2)*(vehicle_request_num[vehicle_idx] / (v2i_rate[vehicle_idx]/2))*800

            #print(i,'mbs delay',(vehicle_request_num[vehicle_idx] / v2i_rate_mbs[vehicle_idx]) *100000)
        request_delay = request_delay/len(vehicle_epoch)*1000

        if print_step % 50 ==0:
            print("---------------------------------------------")
            print('all_vehicle_request_num', all_vehicle_request_num)
            print('step:{} RSU1 cache_efficiency:{}'.format(print_step,cache_efficiency))
            print('step:{} RSU2 cache_efficiency:{}'.format(print_step,cache_efficiency2))
            print('step',print_step,'request delay:%f' %(request_delay))
            print("---------------------------------------------")
        return self.state, reward, cache_efficiency, cache_efficiency2, request_delay

    def reset(self):
        return self.init_state, self.init_cash2, self.init_last_content

    # ------------------------------------------------------------------
    # Phase 4c: Multi-Agent RL methods
    # ------------------------------------------------------------------

    def get_shared_state(self):
        """Return concatenation of RSU1 and RSU2 caches (length 2*cache_size).
        Padded with 0 if either cache has fewer than cache_size items.
        Both agents observe this shared state to enable coordination."""
        s1 = list(self.state)  + [0] * max(0, self.cache_size - len(self.state))
        s2 = list(self.state2) + [0] * max(0, self.cache_size - len(self.state2))
        return s1 + s2

    def step_marl(self, action1, action2, request_dataset, v2i_rate, v2i_rate_mbs,
                  vehicle_epoch, vehicle_request_num, print_step):
        """Two-agent cooperative cache step.

        agent1 controls RSU1 (self.state), agent2 controls RSU2 (self.state2).
        Both agents receive the same joint delay-minimisation reward so that
        cooperation (avoiding duplicate caching) is incentivised.

        action1/action2 in {0, 1}:
          0 — keep current cache unchanged
          1 — replace the 5 least-popular cached items with the 5 most-popular
              uncached items (FL popularity-guided, Phase 4a policy).
        """
        # --- RSU1 replacement (agent1) ---
        if action1 == 1:
            n1 = min(5, len(self.last_content))
            replace1 = self.last_content[:n1]           # top-N uncached by RSU1
            for count in range(n1):
                self.state[-count - 1] = replace1[count]
            self.state = [item for item in self.popular_content
                          if item in self.state]
            self.last_content = [item for item in self.popular_content
                                  if item not in self.state]

        # --- RSU2 replacement (agent2) ---
        if action2 == 1:
            n2 = min(5, len(self.last_content2))
            replace2 = self.last_content2[:n2]          # top-N uncached by RSU2
            for count in range(n2):
                self.state2[-count - 1] = replace2[count]
            self.state2 = [item for item in self.popular_content
                           if item in self.state2]
            self.last_content2 = [item for item in self.popular_content
                                   if item not in self.state2]

        # --- Compute cache efficiencies ---
        all_vehicle_request_num = sum(vehicle_request_num[vehicle_epoch[i]]
                                      for i in range(len(vehicle_epoch)))

        cache_efficiency  = cache_hit_ratio(request_dataset, self.state,
                                            all_vehicle_request_num) / 100
        # cache_efficiency2 counts RSU2 hits for requests NOT already served by RSU1
        cache_efficiency2 = cache_hit_ratio2(request_dataset, self.state2,
                                             self.state, all_vehicle_request_num) / 100

        # --- Joint reward (identical for both agents — cooperative training) ---
        reward = 0
        request_delay = 0
        for i in range(len(vehicle_epoch)):
            v = vehicle_epoch[i]
            n = vehicle_request_num[v]
            r = v2i_rate[v]
            reward += cache_efficiency  * math.exp(-0.0001 * 8000000 / r) * n
            reward += cache_efficiency2 * math.exp(-0.0001 * 8000000 / r
                                                   - 0.4 * 8000000 / 15000000) * n
            reward += (1 - cache_efficiency - cache_efficiency2) \
                      * math.exp(-0.5999 * 8000000 / (r / 2)) * n

            request_delay += cache_efficiency  * n / r * 800
            request_delay += cache_efficiency2 * (n / r + n / 15000000) * 800
            request_delay += (1 - cache_efficiency - cache_efficiency2) \
                             * (n / (r / 2)) * 800

        request_delay = request_delay / len(vehicle_epoch) * 1000

        if print_step % 50 == 0:
            print("---------------------------------------------")
            print('all_vehicle_request_num', all_vehicle_request_num)
            print(f'step:{print_step} RSU1 cache_efficiency:{cache_efficiency}')
            print(f'step:{print_step} RSU2 cache_efficiency:{cache_efficiency2}')
            print(f'step {print_step} request delay:{request_delay:.6f}')
            print("---------------------------------------------")

        return self.get_shared_state(), reward, cache_efficiency, cache_efficiency2, request_delay

    def reset_marl(self):
        """Reset both RSU caches to their initial state and return shared state."""
        self.state         = self.init_state.copy()
        self.state2        = self.init_cash2.copy()
        self.last_content  = self.init_last_content.copy()
        self.last_content2 = self.init_last_content2.copy()
        return self.get_shared_state()

class CacheEnv_density(object):

    def __init__(self, popular_content, cache_size):
        self.cache_size = cache_size
        self.popular_content = popular_content
        self.action_bound = [0, 1]
        self.reward = np.zeros(shape=1, dtype=float)

        # cache list
        if len(self.popular_content)<self.cache_size:
            self.state = self.popular_content

        if len(self.popular_content) >= self.cache_size:
            self.state = random.sample(list(self.popular_content), self.cache_size)

        state1 = []
        for i in range(len(self.popular_content)):
            # 按照内容流行度进行排序
            if self.popular_content[i] in self.state:
                state1.append(self.popular_content[i])
        self.state = state1

        self.last_content = []
        for i in range(len(self.popular_content)):
            if self.popular_content[i] not in self.state:
                self.last_content.append(self.popular_content[i])
        print('self.last_content', len(self.last_content))
        print('self.cache_size', self.cache_size)

        if len(self.last_content)<self.cache_size:
            self.state2 = []
            for i in range(len(self.last_content)):
                if self.last_content[i] not in self.state:
                    self.state2.append(self.last_content[i])

        if len(self.last_content)>=self.cache_size:
            self.state2 = random.sample(list(self.last_content), self.cache_size)

        self.init_state = self.state.copy()
        self.init_cash2 = self.state2.copy()
        self.init_last_content = self.last_content.copy()

    def step_density(self, action, request_dataset, v2i_rate, vehicle_epoch, vehicle_request_num, print_step, vehicle_density):

        action = np.clip(action, *self.action_bound)

        if action == 1:
            if len((self.last_content))>=5:
                replace_content = random.sample(list(self.last_content), 5)
                count = 0
                if count < 5:
                    self.state[-count - 1] = replace_content[count]
                    count += 1
            else:
                replace_content = self.last_content

            state1 = []
            for i in range(len(self.popular_content)):
                # 按照内容流行度进行排序
                if self.popular_content[i] in self.state:
                    state1.append(self.popular_content[i])
            self.state = state1

            last_content = []
            for i in range(len(self.popular_content)):
                if self.popular_content[i] not in self.state:
                    last_content.append(self.popular_content[i])
            self.last_content = last_content

            if len(self.last_content) < self.cache_size:
                self.state2 = []
                for i in range(len(self.last_content)):
                    if self.last_content[i] not in self.state:
                        self.state2.append(self.last_content[i])

            if len(self.last_content) >= self.cache_size:
                self.state2 = random.sample(list(self.last_content), self.cache_size)

        all_vehicle_request_num = 0
        for i in range(len(vehicle_request_num)):
            all_vehicle_request_num += vehicle_request_num[i]
        #print('len(vehicle_request_num)',len(vehicle_request_num))


        cache_efficiency = cache_hit_ratio(request_dataset, self.state,
                                           all_vehicle_request_num)
        cache_efficiency2 = cache_hit_ratio2(request_dataset, self.state2, self.state,
                                             all_vehicle_request_num)
        cache_efficiency = cache_efficiency / 100
        cache_efficiency2 = cache_efficiency2 / 100

        reward = 0
        request_delay = 0

        for i in range(30):
            vehicle_idx = i
            reward += cache_efficiency * math.exp(-0.0001 * 8000000 / v2i_rate[vehicle_idx]) * vehicle_request_num[vehicle_idx]
            reward += cache_efficiency2 * math.exp(-0.0001 * 8000000 / v2i_rate[vehicle_idx]
                                                    -0.4 * 8000000 / 15000000) * vehicle_request_num[vehicle_idx]
            reward += (1-cache_efficiency-cache_efficiency2)\
                                        * math.exp(- 0.5999 * 8000000 / (v2i_rate[vehicle_idx]/2))* vehicle_request_num[vehicle_idx]

            request_delay += cache_efficiency * vehicle_request_num[vehicle_idx] / v2i_rate[vehicle_idx]*800


            #print(i,'local rsu delay', vehicle_request_num[vehicle_idx] / v2i_rate[vehicle_idx]*100000)
            request_delay += cache_efficiency2 * (
                    vehicle_request_num[vehicle_idx] / v2i_rate[vehicle_idx]+vehicle_request_num[vehicle_idx] / 15000000) *800
            #print(i,'neighbouring rsu delay',(vehicle_request_num[vehicle_idx] / v2i_rate[vehicle_idx]+vehicle_request_num[vehicle_idx] / 15000000) *100000)
            request_delay +=(1-cache_efficiency-cache_efficiency2)*(vehicle_request_num[vehicle_idx] / (v2i_rate[vehicle_idx]/2))*800

            #print(i,'mbs delay',(vehicle_request_num[vehicle_idx] / v2i_rate_mbs[vehicle_idx]) *100000)
        request_delay = request_delay/15*1000

        if print_step % 50 == 0:
            print("---------------------------------------------")
            print('all_vehicle_request_num', all_vehicle_request_num)

            print('step:{} RSU1 cache_efficiency:{}'.format(print_step, cache_efficiency))
            print('step:{} RSU2 cache_efficiency:{}'.format(print_step, cache_efficiency2))
            print('step', print_step, 'request delay:%f' % (request_delay))
            print("---------------------------------------------")
        return self.state, reward, cache_efficiency, cache_efficiency2, request_delay

    def reset(self):

        # cache list
        # state = random.sample(list(self.popular_content), 50)
        # self.state = []
        # self.cache2 = []
        # for i in range(len(self.popular_content)):
        #     if self.popular_content[i] not in state:
        #         self.cache2.append(self.popular_content[i])
        #     # 按照内容流行度进行排序
        #     if self.popular_content[i] in state:
        #         self.state.append(self.popular_content[i])

        return self.init_state, self.init_cash2, self.init_last_content
