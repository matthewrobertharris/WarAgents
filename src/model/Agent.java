package model;

import java.util.ArrayList;
import java.util.List;

import main.ProcessTree;
import model.output.Action;
import model.tree.Tree;

public class Agent extends Thing {

	public static final int PICKUP_FOOD = 10;
	public static final int PICKUP_DIRT = 2;
	public static final int LEVEL_PROG = 2;
	public static final int MOVE_HEALTH = 1;
	private static int idCount = 0;
	private Player player;
	private Action action;
	private int speed;
	private int health;
	private int maxHealth;
	private int power;
	private int exp;
	private int level;
	private int dirt;
	private int food;
	private Tree tree;
	private List<AgentHistory> history;
	private int birth;
	private int death;
	private List<Action> actionHistory;
	private XY primary;
	private XY secondary;

	public Agent(int x, int y, Player player, int speed, int maxHealth, int power, Tree tree, int birth) {
		super("Agent" + (idCount++), x, y);
		setPlayer(player);
		setSpeed(speed);
		setMaxHealth(maxHealth);
		setHealth(maxHealth);
		setPower(power);
		setExp(0);
		setLevel(1);
		setDirt(0);
		setFood(0);
		setTree(tree);
		setHistory(new ArrayList<AgentHistory>());
		setBirth(birth);
		setActionHistory(new ArrayList<Action>());
		setVisited(new ArrayList<XY>());
		getVisited().add(new XY(x, y));
		setDeath(-1);
	}

	public XY getPreviousXY() {
		return getVisited().get(getVisited().size() - 1);
	}

	public Action getPreviousAction() {
		if (getActionHistory().isEmpty()) {
			return null;
		}
		return getActionHistory().get(getActionHistory().size() - 1);
	}

	public XY getPrimary() {
		return primary;
	}

	public void setPrimary(XY primary) {
		this.primary = primary;
	}

	public XY getSecondary() {
		return secondary;
	}

	public void setSecondary(XY secondary) {
		this.secondary = secondary;
	}

	public int getDeath() {
		return death;
	}

	public void setDeath(int death) {
		this.death = death;
	}

	public List<Action> getActionHistory() {
		return actionHistory;
	}

	public void setActionHistory(List<Action> actionHistory) {
		this.actionHistory = actionHistory;
	}

	public int getBirth() {
		return birth;
	}

	public void setBirth(int birth) {
		this.birth = birth;
	}

	public void addHistory(AgentHistory agentHistory) {
		getHistory().add(agentHistory);
	}

	public List<AgentHistory> getHistory() {
		return history;
	}

	public void setHistory(List<AgentHistory> history) {
		this.history = history;
	}

	public Tree getTree() {
		return tree;
	}

	public void setTree(Tree tree) {
		this.tree = tree;
	}

	public static int getIdCount() {
		return idCount;
	}

	public static void setIdCount(int idCount) {
		Agent.idCount = idCount;
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

	public int getSpeed() {
		return speed;
	}

	public void setSpeed(int speed) {
		this.speed = speed;
	}

	public int getHealth() {
		return health;
	}

	public void setHealth(int health) {
		if (health > maxHealth) {
			this.health = getMaxHealth();
		} else {
			this.health = health;
		}
	}

	public int getMaxHealth() {
		return maxHealth;
	}

	public void setMaxHealth(int maxHealth) {
		this.maxHealth = maxHealth;
	}

	public int getPower() {
		return power;
	}

	public void setPower(int power) {
		this.power = power;
	}

	public int getExp() {
		return exp;
	}

	public void setExp(int exp) {
		this.exp = exp;
		if (getExp() > Math.pow(LEVEL_PROG, getLevel())) {
			setLevel(getLevel() + 1);
		}
	}

	public int getLevel() {
		return level;
	}

	private void setLevel(int level) {
		this.level = level;
	}

	public Player getPlayer() {
		return player;
	}

	public void setPlayer(Player player) {
		this.player = player;
	}

	public Action getAction() {
		return action;
	}

	public void setAction(Action action) {
		this.action = action;
		getActionHistory().add(getAction());
	}

	// Use decision tree
	public boolean update(Map map) {
		try {
			getHistory().add(new AgentHistory(this));
			if (getHealth() < 1) {
				Action.death(this, map);
				return false;
			} else {
				setAction(ProcessTree.decide(getTree().getRoot(), this, map));
				return getAction().action(this, map);
			}
		} catch (Exception e) {
			System.out.println(e);
			throw e;
		}
	}

	public String toString() {
		String output = super.toString();
		output += " player=" + getPlayer().getName();
		output += " tree=" + getTree().getName();
		output += " action=" + getAction();
		output += " food=" + getFood();
		output += " dirt=" + getDirt();
		output += " health=" + getHealth();
		output += " maxHealth=" + getMaxHealth();
		output += " power=" + getPower();
		output += " speed=" + getSpeed();
		return output;
	}
}
