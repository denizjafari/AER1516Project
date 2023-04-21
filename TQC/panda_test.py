__author__ = 'Saeid Alavi'


import gym
#import gymnasium as gym
import panda_gym

env = gym.make('PandaReach-v1', render=True)

#env = gym.make('PandaReach-v1', render_mode="human")

obs = env.reset()
done = False
while not done:
    action = env.action_space.sample() # random action
    obs, reward, done, info = env.step(action)

env.close()


# running in the loop
#env = gym.make('PandaReach-v1', render_mode="human")

observation, info = env.reset()

for _ in range(10000):
    action = env.action_space.sample() # random action
    observation, reward, terminated, truncated, info = env.step(action)

    if terminated or truncated:
        observation, info = env.reset()

env.close()