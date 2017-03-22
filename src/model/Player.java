package model;

import java.util.ArrayList;
import java.util.List;

import model.tree.Tree;

public class Player {

	private String name;
	private int agentHealth;
	private int agentSpeed;
	private int agentPower;
	private List<Tree> trees;
	private int maxAgents;
	private List<Agent> allAgents;
	private List<Agent> currentAgents;

	public Player(String name, int agentHealth, int agentSpeed, int agentPower, List<Tree> trees, int maxAgents,
			List<Agent> agents) {
		setName(name);
		setAgentHealth(agentHealth);
		setAgentSpeed(agentSpeed);
		setAgentPower(agentPower);
		setTrees(trees);
		setAllAgents(agents);
		setMaxAgents(maxAgents);

	}

	public Player(int x, int y, String name, int agentHealth, int agentSpeed, int agentPower, List<Tree> trees, int maxAgents,
			List<Agent> agents) {
		Agent agent = new Agent(x, y, this, agentSpeed, agentHealth, agentPower, trees.get(0), 0);
		agents.add(agent);
		setName(name);
		setAgentHealth(agentHealth);
		setAgentSpeed(agentSpeed);
		setAgentPower(agentPower);
		setTrees(trees);
		setCurrentAgents(agents);
		setAllAgents(new ArrayList<Agent>());
		for (Agent a : getCurrentAgents()) {
			getAllAgents().add(a);
		}
		setMaxAgents(maxAgents);
	}

	public int getMaxAgents() {
		return maxAgents;
	}

	public void setMaxAgents(int maxAgents) {
		this.maxAgents = maxAgents;
	}

	public List<Agent> getAllAgents() {
		return allAgents;
	}

	public void setAllAgents(List<Agent> allAgents) {
		this.allAgents = allAgents;
	}

	public List<Agent> getCurrentAgents() {
		return currentAgents;
	}

	public void setCurrentAgents(List<Agent> currentAgents) {
		this.currentAgents = currentAgents;
	}

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public List<Tree> getTrees() {
		return trees;
	}

	public void setTrees(List<Tree> trees) {
		this.trees = trees;
	}

	public int getAgentHealth() {
		return agentHealth;
	}

	public void setAgentHealth(int agentHealth) {
		this.agentHealth = agentHealth;
	}

	public int getAgentSpeed() {
		return agentSpeed;
	}

	public void setAgentSpeed(int agentSpeed) {
		this.agentSpeed = agentSpeed;
	}

	public int getAgentPower() {
		return agentPower;
	}

	public void setAgentPower(int agentPower) {
		this.agentPower = agentPower;
	}

	public void addAgent(Agent agent) {
		getAllAgents().add(agent);
		getCurrentAgents().add(agent);

	}

	public int currentAgents() {
		return getCurrentAgents().size();
	}

	public boolean hasSpace() {
		return currentAgents() < getMaxAgents();
	}

	public String toString() {
		String output = "Name=" + getName();
		output += " maxAgents=" + getMaxAgents();
		output += " agentPower=" + getAgentPower();
		output += " agentHealth=" + getAgentHealth();
		output += " agentSpeed=" + getAgentSpeed();
		output += "\nagents=";
		for (Agent agent : getCurrentAgents()) {
			output += "\t" + agent.toString() + "\n";
		}
		output += "trees=";
		for (Tree tree : getTrees()) {
			output += "\t" + tree.toString() + "\n";
		}
		return output;
	}
}
