import numpy as np
import torch
import random
import gym
import mujoco_py

import progressbar as pb           # tracking time while training
import matplotlib.pyplot as plt    # plotting scores

from ddpg import ddpgAgent
from rollout import RolloutWorker
from her_sampler import make_sample_her_transitions
from parallelEnvironment import parallelEnv

DEFAULT_PARAMS = {
    # environment
    'env_name': 'FetchPickAndPlace-v1',              # 'FetchReach-v1', 'FetchPush-v1', 'FetchPickAndPlace-v1', 'FetchSlide-v1'
    'seed': 0,                                # random seed for environment, torch, numpy, random packages
    'T': 50,                                  # maximum episode length

    # training setup
    'replay_strategy': 'none',              # 'none' for vanilla ddpg, 'future' for HER
    'num_workers': 16,                        # number of parallel workers
    'n_epochs': 200,                          # number of epochs, HER paper: 200 epochs (i.e. maximum of 8e6 timesteps)
    'n_cycles': 50,                           # number of cycles per epoch, HER paper: 50 cycles
    'n_optim': 40,                            # number of optimization steps every cycle
    'n_eval_rollouts': 10,                    # number of rollouts in evaluation, rollouts are episodes from num_workers

    # Agent hyper-parameters
    'lr_actor': 0.001,                        # learning rate actor network
    'lr_critic': 0.001,                       # learning rate critic network
    'buffer_size': int(1e6),                  # replay-buffer size
    'tau': 0.05,                              # soft update of network coefficient, 1-tau = polyak coefficient
    'batch_size': 256,                        # batch size per thread
    'gamma': 0.98,                            # discount factor
    'clip_return': 50.,                       # return clipping
    'clip_obs': 200.,                         # observation clipping
    'clip_action': 1.,                        # action clipping

    # exploration
    'random_eps': 0.2,                        # probability of random action in hypercube of possible actions
    'noise_eps': 0.05,                        # std of gaussian noise added actions

    # normalization
    'norm_eps': 0.01,                         # eps for observation normalization
    'norm_clip': 5.,                           # normalized observations are clipped to this values

    # location (path) of files for report
    'results_path': './tmp_results'
}


def set_seeds(seed: int = 0):
    """
    Set the random seed to all packages.
    Note: Parallel workers will have different seeds in each environment based on this seed.
    @param seed: (int) seed for torch, numpy, random. By default zero.
    """
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    pass


def dims_and_reward_fun(env_name: str):
    """
    Get dimensions of observations, action, goal and the used reward function.
    @param env_name: (str) name of gym environment
    @return: dict for dimensions, reward function of environment
    """
    env = gym.make(env_name)
    env.reset()
    obs, _, _, _ = env.step(env.action_space.sample())
    dims = {
        'o': obs['observation'].shape[0],
        'u': env.action_space.shape[0],
        'g': obs['desired_goal'].shape[0],
        'info_is_success': 1,
    }
    return dims, env.compute_reward


def train(agent, rollout_worker, evaluation_worker):
    """
    Train DDPG (+ HER is optional) with multiple workers and save values to scores.
    @param agent: (object) DDPG agent
    @param rollout_worker: (object) worker for training the networks
    @param evaluation_worker: (object) worker for evaluating current networks
    @return: scores i.e. success-rate of agent from evaluating worker in a list
    """
    scores = []
    print("Training environment", DEFAULT_PARAMS['env_name'], "started...")
    print("Maximum number of training timesteps is ",
          DEFAULT_PARAMS['n_epochs'] * DEFAULT_PARAMS['n_cycles'] * DEFAULT_PARAMS['T'] * DEFAULT_PARAMS['num_workers'],
          "in", DEFAULT_PARAMS['n_epochs'], "epochs with", DEFAULT_PARAMS['num_workers'], "parallel workers.")

    # widget bar to display progress during training
    widget = ['training loop: ', pb.Percentage(), ' ', pb.Bar(), ' ', pb.ETA()]
    timer = pb.ProgressBar(widgets=widget, maxval=DEFAULT_PARAMS['n_epochs']).start()

    for epoch in range(DEFAULT_PARAMS['n_epochs']):
        for _ in range(DEFAULT_PARAMS['n_cycles']):
            episode = rollout_worker.generate_rollouts()  # generate episodes with every parallel environment
            agent.store_episode(episode)                  # store experiences as whole episodes
            for _ in range(DEFAULT_PARAMS['n_optim']):    # optimize target network
                agent.learn()
            agent.soft_update_target_networks()           # update target network

        # evaluating agent for report
        eval_scores = []
        for _ in range(DEFAULT_PARAMS['n_eval_rollouts']):
            evaluation_worker.generate_rollouts()
            eval_scores.append(evaluation_worker.success_rate)
        print('\n \tEpoch: {} / {}, Success: {:.4f}'.format(epoch, DEFAULT_PARAMS['n_epochs'], np.mean(eval_scores)))
        scores.append(np.mean(eval_scores))

        timer.update(epoch)
    timer.finish()
    return scores


def main():
    """
    Main function: Training ddpg agent (optional with HER) as defined in DEFAULT_PARAMS and saving stats.
    """
    set_seeds(DEFAULT_PARAMS['seed'])

    env = parallelEnv(DEFAULT_PARAMS['env_name'], n=DEFAULT_PARAMS['num_workers'], seed=DEFAULT_PARAMS['seed'])

    DEFAULT_PARAMS['dims'], DEFAULT_PARAMS['reward_fun'] = dims_and_reward_fun(DEFAULT_PARAMS['env_name'])

    DEFAULT_PARAMS['sample_her_transitions'] = make_sample_her_transitions(
        replay_strategy=DEFAULT_PARAMS['replay_strategy'], replay_k=4, reward_fun=DEFAULT_PARAMS['reward_fun'])


    agent = ddpgAgent(DEFAULT_PARAMS)

    rollout_worker = RolloutWorker(env, agent, DEFAULT_PARAMS)
    evaluation_worker = RolloutWorker(env, agent, DEFAULT_PARAMS, evaluate=True)

    scores = train(agent, rollout_worker, evaluation_worker)

    # save networks and stats ------------------------------------------------------------------------------------------
    agent.save_checkpoint(DEFAULT_PARAMS['results_path'], DEFAULT_PARAMS['env_name'])
    np.savetxt(DEFAULT_PARAMS['results_path']+'/scores_'+DEFAULT_PARAMS['env_name']+'_' +
               str(DEFAULT_PARAMS['seed'])+'.csv', scores, delimiter=',')
    fig = plt.figure()
    fig.add_subplot(111)
    plt.plot(np.arange(len(scores)), scores)
    plt.title("Success rate")
    plt.xlabel("Epochs")
    plt.ylabel("Success rate")
    plt.savefig(DEFAULT_PARAMS['results_path']+'/scores_'+DEFAULT_PARAMS['env_name']+'_' +
                str(DEFAULT_PARAMS['seed'])+'.png')
    plt.show()

if __name__ == '__main__':
    main()
