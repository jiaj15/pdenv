"""Wrappers for intergating imitation reward function."""
import gym
import gym_panda
from gym_panda.wrapper_env.VAE import VAE
import torch
import numpy as np
import copy
import pickle

# EPSILON = 0.01

# class SkipStepsWrapper(gym.Wrapper):
#     """ Wrapper to use VAE output for rewards, with max episode length = 40000"""
#     def __init__(self, env):
#         gym.Wrapper.__init__(self, env)
#         self.env = env
#         self.time_step = 0
#         self.eps_len = 40000

#         self.model = VAE(3)
#         model_dict = torch.load('/home/jingjia/iliad/logs/models/pandaenv-random-v0_0.005_vae.pt', map_location='cpu')
#         self.model.load_state_dict(model_dict)
#         self.model.eval

#     def reset(self):
#         self.prev_state = self.env.reset()['ee_position']
#         self.expect_state = self.model.get_next_states(torch.FloatTensor(self.prev_state)).detach().numpy()
#         self.time_step = 0
#         return self.prev_state


#     def step(self, action):
#         self.env.step(action)
#         self.time_step += 1

#         done = (self.time_step > 400 * self.eps_len)
#         state = self.env.panda.state['ee_position']
#         dis = np.linalg.norm(state - self.expect_state)
#         if  dis < EPSILON:
#             # update expect state
#             self.prev_state = state
#             self.expect_state = self.model.get_next_states(torch.FloatTensor(self.prev_state)).detach().numpy()
#         reward = - dis
#         info = {}
#         self.prev_state = copy.deepcopy(state)
#         return state, reward, done, info


#     def close(self):
#         self.env.close()

class CircleVAEExpert():
    def __init__(self):
        self.model = VAE(3)
        model_dict = torch.load('/home/jingjia/iliad/logs/data/0206/pandaenv-random-v0_0.005_vae.pt', map_location='cpu')
        # model_dict = torch.load('/iliad/u/jingjia/multi_agent/pandaenv-random-v0_0.005_vae.pt', map_location='cpu')
        self.model.load_state_dict(model_dict)
        self.model.eval

    def get_next_states(self, state):
        expect_state = self.model.get_next_states(torch.FloatTensor(state)).detach().numpy()
        expect_state[1]=0
        return expect_state


class SkipStepsWrapperVAE(gym.Wrapper):
    """ Wrapper to use CircleExpert for rewards, with max episode length = 40000."""
    def __init__(self, env):
        gym.Wrapper.__init__(self, env)
        self.env = env
        self.time_step = 0
        self.eps_len = 2000
        self.EPSILON = 0.02
        self.model = CircleVAEExpert()

    def reset(self):
        # state = self.env.reset()['ee_position']
        self.env.reset()
        self.prev_state = self.env.panda.state['ee_position']
        self.expect_state = self.model.get_next_states(self.prev_state)
        state =  np.concatenate((
            self.env.panda.state['joint_position'],# 5
            self.env.panda.state['joint_velocity'],# 5
            self.env.panda.state['joint_torque'],# 5
            self.env.panda.state['ee_position'],# 3
            self.env.panda.state['ee_euler'], # 3
            ), axis=None)
        self.time_step = 0
        return state


    def step(self, action):
        self.env.step(action)
        self.time_step += 1

        state = self.env.panda.state['ee_position']
        done = (self.time_step > self.eps_len)
        dis = 10 * np.linalg.norm(state - self.expect_state)
        reward = - (dis**2)
        #if  dis < 10 * self.EPSILON:
        self.expect_state = self.model.get_next_states(state)
        info = {}
        self.prev_state = copy.deepcopy(state)
        full_state =  np.concatenate((
            self.env.panda.state['joint_position'],# 5
            self.env.panda.state['joint_velocity'],# 5
            self.env.panda.state['joint_torque'],# 5
            self.env.panda.state['ee_position'],# 3
            self.env.panda.state['ee_euler'], # 3
            ), axis=None)
        return full_state, reward, done, info


    def close(self):
        self.env.close()
        
class CircleExpert(object):
    """ Expert to draw a circle centered at (cx, cy) with a radius of 0.2."""
    def __init__(self, env=None):
        self.r = 0.2
        self.step = 0.1 * np.pi #0.2 * np.pi
        self.cx = 0.35
        self.cy = 0.52

    
    def get_next_states(self, state):
        cur_pos = np.array([state[0] - self.cx, state[2] - self.cy])
        cur_the = np.arctan2(cur_pos[1], cur_pos[0])
        next_the = cur_the
        # if abs(np.sqrt(np.sum(np.square(cur_the))) - self.r) < EPSILON:
        #     # if on the circle, move forward by one step
        next_the += self.step
        next_pos = np.array([self.cx + self.r * np.cos(next_the), 0, self.cy + self.r * np.sin(next_the)])
        return next_pos

class collectDemonsWrapper(gym.Wrapper):
    def __init__(self, env):
        gym.Wrapper.__init__(self, env)
        self.env = env
        self.time_step = 0
        self.eps_len = 500
        

    def _random_reset(self):
        # random pick start pos
        theta = np.random.uniform(low=0.0, high=2*np.pi)
        phi = np.random.uniform(low=0.0, high=2*np.pi)
        r = np.random.uniform(low=0.1, high=0.1)
        dpos = [0.6+r*np.sin(theta)*np.cos(phi),r*np.sin(theta)*np.sin(phi),0.5+r*np.cos(theta)]
        self.env.panda._set_start(position=dpos)

    def reset(self):
        # state = self.env.reset()['ee_position']
        self.env.reset()
        self._random_reset()

        state = self.env.panda.state['ee_position']
        self.time_step = 0
        
        return state


    def step(self, action, mode):
        self.env.step(action, mode=mode)       

        state = self.env.panda.state['ee_position']
        self.time_step += 1
        done = (self.time_step >= self.eps_len - 1)
        reward = 0
        info = {}
        self.prev_state = copy.deepcopy(state)
        
        return state, reward, done, info


    def close(self):
        self.env.close()


class infeasibleWrapper(gym.Wrapper):
    def __init__(self, env):
        gym.Wrapper.__init__(self, env)
        self.env = env
        self.time_step = 0
        self.eps_len = 500
        self.gt_data =  pickle.load(open('/home/jingjia/iliad/logs/data/infeasible_traj_3.pkl', 'rb'))
        
        # self.gt =  pickle.load(open('/iliad/u/jingjia/multi_agent/gym_panda/gym_panda/panda_bullet/infeasible_traj_1.pkl', 'rb'))

    def _random_select(self, state, idx=None):
        # random pick start pos
        if idx is None:
            self.gt_num = np.random.choice(self.gt_data.shape[0])
        else:
            self.gt_num = idx
        self.gt = self.gt_data[self.gt_num, :, :]
       
        pos = self.gt[0, :]
        # pos[1] = 0
        self.env.panda._set_start(position=pos)
        print(self.env.panda.state['ee_position'], pos)

    def reset(self,idx=None):
        # state = self.env.reset()['ee_position']
        
        self.env.reset()
        state = self.env.panda.state['ee_position']
        self._random_select(state,idx)

        state =  np.concatenate((
            self.env.panda.state['joint_position'],# 5
            self.env.panda.state['joint_velocity'],# 5
            self.env.panda.state['joint_torque'],# 5
            self.env.panda.state['ee_position'],# 3
            self.env.panda.state['ee_euler'], # 3
            ), axis=None)
        self.time_step = 0
        
        return state


    def step(self, action):
        self.env.step(action)       

        state = self.env.panda.state['ee_position']
        self.time_step += 1
        done = (self.time_step >= self.eps_len - 1)
        dis = 10 * np.linalg.norm(state - self.gt[self.time_step,:])
        reward = - (dis**2)
        info = {}
        self.prev_state = copy.deepcopy(state)
        full_state =  np.concatenate((
            self.env.panda.state['joint_position'],# 5
            self.env.panda.state['joint_velocity'],# 5
            self.env.panda.state['joint_torque'],# 5
            self.env.panda.state['ee_position'],# 3
            self.env.panda.state['ee_euler'], # 3
            ), axis=None)
        info['dis'] = dis/10;
        
        return full_state, reward, done, info


    def close(self):
        self.env.close()



class SkipStepsWrapperNoVAE(gym.Wrapper):
    """ Wrapper to use CircleExpert for rewards, with max episode length = 40000."""
    def __init__(self, env):
        gym.Wrapper.__init__(self, env)
        self.env = env
        self.time_step = 0
        self.eps_len = 500
        self.EPSILON = 0.02
        self.model = CircleExpert()

    def reset(self):
        # state = self.env.reset()['ee_position']
        self.env.reset()
        self.prev_state = self.env.panda.state['ee_position']
        self.expect_state = self.model.get_next_states(self.prev_state)
        state =  np.concatenate((
            self.env.panda.state['joint_position'],# 5
            self.env.panda.state['joint_velocity'],# 5
            self.env.panda.state['joint_torque'],# 5
            self.env.panda.state['ee_position'],# 3
            self.env.panda.state['ee_euler'], # 3
            ), axis=None)
        self.time_step = 0
        return state


    def step(self, action):
        self.env.step(action)
        self.time_step += 1

        state = self.env.panda.state['ee_position']
        done = (self.time_step > self.eps_len)
        dis = 10 * np.linalg.norm(state - self.expect_state)
        reward = - (dis**2)
        #if  dis < 10 * self.EPSILON:
        self.expect_state = self.model.get_next_states(state)
        info = {}
        self.prev_state = copy.deepcopy(state)
        full_state =  np.concatenate((
            self.env.panda.state['joint_position'],# 5
            self.env.panda.state['joint_velocity'],# 5
            self.env.panda.state['joint_torque'],# 5
            self.env.panda.state['ee_position'],# 3
            self.env.panda.state['ee_euler'], # 3
            ), axis=None)
        return full_state, reward, done, info


    def close(self):
        self.env.close()


class LineExpert(object):
    """ Drawing a line x = 0.45 and stay at any points with y >= 0.7."""
    def __init__(self, env=None):
        self.r = 0.4
        self.step = 0.05
        self.ymax = 0.75
        # self.cy = 0.52
        self.EPSILON = 0.05
    
    def get_next_states(self, state):
        cur_x = state[0]
        cur_y = state[2]
        # if (abs(cur_x - self.xstart) < self.EPSILON):
        next_pos = np.array([self.xstart , 0, max(cur_y + self.step, self.ymax)])
        # else:
        #     next_pos = np.array([self.xstart , 0, self.ystart])        
        return next_pos
    def set_start(self, state):
        self.xstart = state[0]
        self.ystart = state[2]
    


class SkipStepsWrapperNoVAELine(gym.Wrapper):
    """ Wrapper to use LineExpert for rewards, with max episode length = 4000."""
    def __init__(self, env):
        gym.Wrapper.__init__(self, env)
        self.env = env
        self.time_step = 0
        self.eps_len = 500
        self.EPSILON = 0.02
        self.model = LineExpert()

    def reset(self):
        # state = self.env.reset()['ee_position']
        self.env.reset()
        self.model.set_start(self.env.panda.state['ee_position'])
        self.prev_state = self.env.panda.state['ee_position']
        self.expect_state = self.model.get_next_states(self.prev_state)
        state =  np.concatenate((
            self.env.panda.state['joint_position'],# 5
            self.env.panda.state['joint_velocity'],# 5
            self.env.panda.state['joint_torque'],# 5
            self.env.panda.state['ee_position'],# 3
            self.env.panda.state['ee_euler'], # 3
            ), axis=None)
        self.time_step = 0
        return state


    def step(self, action):
        self.env.step(action)
        self.time_step += 1

        state = self.env.panda.state['ee_position']
        full_state =  np.concatenate((
            self.env.panda.state['joint_position'],# 5
            self.env.panda.state['joint_velocity'],# 5
            self.env.panda.state['joint_torque'],# 5
            self.env.panda.state['ee_position'],# 3
            self.env.panda.state['ee_euler'], # 3
            ), axis=None)
        
        done = (self.time_step > self.eps_len)
        dis = 10 * np.linalg.norm(state - self.expect_state)
        reward = - (dis**2)
        if  dis < self.EPSILON:
            print("GOOD")
            self.expect_state = self.model.get_next_states(state)
        info = {}
        self.prev_state = copy.deepcopy(state)
        
        return full_state, reward, done, info


    def close(self):
        self.env.close()


class SkipStepsWrapperNoVAEPoint(gym.Wrapper):
    """ Wrapper for reaching a point, with max episode length = 40000."""
    def __init__(self, env):
        gym.Wrapper.__init__(self, env)
        self.env = env
        self.time_step = 0
        self.goal = np.array([0.45, 0, 0.6])
        self.eps_len = 500

    def reset(self):
        # state = self.env.reset()['ee_position']
        self.env.reset()
        state =  np.concatenate((
            self.env.panda.state['joint_position'],# 5
            self.env.panda.state['joint_velocity'],# 5
            self.env.panda.state['joint_torque'],# 5
            self.env.panda.state['ee_position'],# 3
            self.env.panda.state['ee_euler'], # 3
            ), axis=None)
        self.time_step = 0
        return state


    def step(self, action, expert=False):
        if expert:
            self.env.step(action, mode=1)
        else:
            self.env.step(action)

        self.time_step += 1

        state = self.env.panda.state['ee_position']
        done =(self.time_step > self.eps_len)
        dis = 10 * np.linalg.norm(state - self.goal)
        reward = - (dis ** 2)
        # if  dis < 0.02:
        #     reward = 1.0    
        info = {}
        
        full_state =  np.concatenate((
            self.env.panda.state['joint_position'],# 5
            self.env.panda.state['joint_velocity'],# 5
            self.env.panda.state['joint_torque'],# 5
            self.env.panda.state['ee_position'],# 3
            self.env.panda.state['ee_euler'], # 3
            ), axis=None)
        return full_state, reward, done, info

    def close(self):
        self.env.close()
