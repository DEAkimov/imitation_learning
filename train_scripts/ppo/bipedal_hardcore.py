import gym
import torch

import utils.env_wrappers as wrappers
from utils.vec_env import SubprocVecEnv
from utils.utils import create_log_dir
from algorithms.nn.actor_critic import ActorCriticTwoMLP
from algorithms.normalization import RunningMeanStd
from algorithms.agents.base_agent import AgentInference
from algorithms.agents.ppo import PPO
from trainers.on_policy import OnPolicyTrainer


train_env_num = 16
test_env_num = 4
distribution = 'Beta'
device = torch.device('cpu')
log_dir = 'logs_py/bipedal_hardcore/exp_0/'

actor_critic_args = {
    'observation_size': 24, 'hidden_size': 128, 'action_size': 4,
    'distribution': distribution
}
agent_train_args = {
    'ppo_n_epoch': 5, 'ppo_n_mini_batches': 4,
    'ppo_epsilon': 0.1
}
trainer_args = {'warm_up_steps': 20, 'n_plot_agents': 1, 'log_dir': log_dir}
train_args = {
    'n_epoch': 20, 'n_steps_per_epoch': 2_000,
    'rollout_len': 64, 'n_tests_per_epoch': 100,
}


def make_env():
    def make():
        env = gym.make('BipedalWalker-v3')
        env = wrappers.ContinuousActionWrapper(env)
        env = wrappers.ActionRepeatAndRenderWrapper(env)
        return env
    return make


def make_vec_env(n_envs):
    vec_env = SubprocVecEnv([make_env() for _ in range(n_envs)])
    return vec_env


def make_agent_online():
    actor_critic_online = ActorCriticTwoMLP(**actor_critic_args)
    obs_normalizer = RunningMeanStd()
    rew_scaler = RunningMeanStd()
    value_normalizer = RunningMeanStd()
    agent = AgentInference(
        actor_critic_online, device, distribution,
        obs_normalizer=obs_normalizer,
        reward_scaler=rew_scaler,
        value_normalizer=value_normalizer
    )
    return agent


def make_agent_train():
    actor_critic_train = ActorCriticTwoMLP(**actor_critic_args)
    obs_normalizer = RunningMeanStd()
    rew_scaler = RunningMeanStd()
    value_normalizer = RunningMeanStd()
    agent = PPO(
        actor_critic_train, device, distribution,
        obs_normalizer=obs_normalizer,
        reward_scaler=rew_scaler,
        value_normalizer=value_normalizer,
        **agent_train_args
    )
    return agent


def main():
    create_log_dir(log_dir, __file__)

    train_env = make_vec_env(train_env_num)
    test_env = make_vec_env(test_env_num)

    agent_online = make_agent_online()
    agent_train = make_agent_train()
    agent_online.load_state_dict(agent_train.state_dict())

    trainer = OnPolicyTrainer(
        agent_online, agent_train, train_env,
        **trainer_args,
        test_env=test_env
    )
    trainer.train(**train_args)

    train_env.close()
    test_env.close()


if __name__ == '__main__':
    main()
