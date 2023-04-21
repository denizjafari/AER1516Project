__author__ = 'Saeid Alavi'

import gym
from stable_baselines3.common.env_checker import check_env
env = gym.make("FetchPickAndPlace-v1")

print("Observation space:", env.observation_space)
print("Shape:", env.observation_space.shape)
# Discrete(2) means that there is two discrete actions
print("Action space:", env.action_space)

# The reset method is called at the beginning of an episode
obs = env.reset()
# Sample a random action
action = env.action_space.sample()
print("Sampled action:", action)
obs, reward, done, info = env.step(action)
# Note the obs is a numpy array
# info is an empty dict for now but can contain any debugging info
# reward is a scalar
print(obs)
print( reward, done, info)
print("here")
#print(check_env(env, warn=True))