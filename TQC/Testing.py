__author__ = 'Saeid Alavi'
python -m rl_zoo3.record_video --algo ppo --env BipedalWalkerHardcore-v3 -n 1000 --load-checkpoint 10000



python -m rl_zoo3.record_training --algo ppo --env CartPole-v1 -n 1000 -f logs --deterministic