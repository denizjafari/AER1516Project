__author__ = 'Saeid Alavi'

#import gym

import gymnasium as gym
import panda_gym
from stable_baselines3 import DDPG

env = gym.make("PandaReach-v3")
model = DDPG(policy="MultiInputPolicy", env=env)
model.train(30_000)

