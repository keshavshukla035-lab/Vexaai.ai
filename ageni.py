from uagents import Agent

from protocols import form_protocol

agent = Agent()

# The chat protocol, system prompt, and all handlers live in protocols.py.
agent.include(form_protocol, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
