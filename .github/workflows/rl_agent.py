import numpy as np
import random
import pickle

class RLAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.q_table = np.zeros((state_size, action_size))
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.exploration_rate = 1.0
        self.exploration_decay = 0.99
    
    def choose_action(self, state):
        if random.uniform(0, 1) < self.exploration_rate:
            return random.randint(0, self.action_size - 1)
        return np.argmax(self.q_table[state, :])
    
    def learn(self, state, action, reward, next_state):
        predict = self.q_table[state, action]
        target = reward + self.discount_factor * np.max(self.q_table[next_state, :])
        self.q_table[state, action] += self.learning_rate * (target - predict)


agent = RLAgent(state_size=10, action_size=5)  # Example: 10 states, 5 actions
# Training process (example loop)
for episode in range(1000):
    state = random.randint(0, 9)  # Example random initial state
    action = agent.choose_action(state)
    reward = random.randint(-10, 10)  # Example reward
    next_state = random.randint(0, 9)
    agent.learn(state, action, reward, next_state)

# Save Q-table
with open('q_table.pkl', 'wb') as f:
    pickle.dump(agent.q_table, f)
