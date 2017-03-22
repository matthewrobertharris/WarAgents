package model;

import model.output.Action;
import model.tree.Tree;

public class AgentHistory {
	private Action action;
	private int health;
	private int exp;
	private int dirt;
	private int food;
	private Tree tree;

	public AgentHistory(Agent agent) {
		this(agent.getAction(), agent.getHealth(), agent.getExp(), agent.getDirt(), agent.getFood(), agent.getTree());
	}

	public AgentHistory(Action action, int health, int exp, int dirt, int food, Tree tree) {
		setAction(action);
		setHealth(health);
		setExp(exp);
		setDirt(dirt);
		setFood(food);
		setTree(tree);
	}

	public Action getAction() {
		return action;
	}

	public void setAction(Action action) {
		this.action = action;
	}

	public int getHealth() {
		return health;
	}

	public void setHealth(int health) {
		this.health = health;
	}

	public int getExp() {
		return exp;
	}

	public void setExp(int exp) {
		this.exp = exp;
	}

	public int getDirt() {
		return dirt;
	}

	public void setDirt(int dirt) {
		this.dirt = dirt;
	}

	public int getFood() {
		return food;
	}

	public void setFood(int food) {
		this.food = food;
	}

	public Tree getTree() {
		return tree;
	}

	public void setTree(Tree tree) {
		this.tree = tree;
	}

	public String toString() {
		String output = " health=" + getHealth();
		output += " exp=" + getExp();
		output += " dirt=" + getDirt();
		output += " food=" + getFood();
		output += " test=" + getAction();
		if (getAction() != null) {
			output += " Action=" + getAction().toString();
		}
		output += " node=" + getTree().getName();

		return output;
	}
}
