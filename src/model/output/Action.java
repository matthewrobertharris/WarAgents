package model.output;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import model.Agent;
import model.AgentHistory;
import model.Map;
import model.Tile;

public abstract class Action {

	public enum Activity {
		ATTACK_DOWN, ATTACK_LEFT, ATTACK_RIGHT, ATTACK_UP, 
		
		CHANGE_TREE, 
		
		DEFEND, 
		
		DROP_DIRT, DROP_FOOD, 
		
		EAT, 
		
		LIFT_DIRT, LIFT_FOOD, 
		
		MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, MOVE_UP, 
		
		REPRODUCE,
		
		SET_PRIMARY, CLEAR_PRIMARY, SET_SECONDARY, CLEAR_SECONDARY,
		
		CONFUSED,
		 
		DEATH
	};
	public abstract boolean action(Agent agent, Map map);
	public abstract Activity getActivity();
	
	protected boolean attack(Agent attacker, Agent defender, Map map) {
		int health = defender.getHealth();
		int power = attacker.getPower();
		int defenderHeight = map.getTile(defender.getCurrentPos()).getDirt();
		int attackerHeight = map.getTile(attacker.getCurrentPos()).getDirt();
		int heightDiff = attackerHeight - defenderHeight;
		if (defender.getAction() instanceof Defend) {
			power /= 2;
		}
		switch (heightDiff) {
		case 0:
			// no change in power
			break;
		case 1:
			power *= 2;
			break;
		case 2:
			power *= 3;
			break;
		case 3:
			power *= 4;
			break;
		case -1:
			power /= 2;
			break;
		case -2:
			power /= 3;
			break;
		default:
			return false;
		}
		defender.setHealth(health - power);
		if (defender.getHealth() < 1) {
			death(defender, map);
		}
		return true;
	}

	public static boolean death(Agent agent, Map map) {
		int health = agent.getMaxHealth();
		int x = agent.getX();
		int y = agent.getY();
		agent.setDeath(map.getTime());
		agent.addHistory(new AgentHistory(agent));
		map.getTile(x, y).addFood((int) (health * 0.25));
		map.getTile(x, y).setAgent(null);
		agent.getPlayer().getCurrentAgents().remove(agent);
		map.getAllAgents().remove(agent);
		return true;
	}
	
	protected static int[] findPosition(Map map, int x, int y) {
		Random rnd = new Random();
		List<Integer> positions = new ArrayList<Integer>();
		for (int i = 0; i < 4; i++) {
			positions.add(i);
		}
		for (int i = 0; i < 4; i++) {
			int choice = rnd.nextInt(positions.size());
			int pos = positions.get(choice);
			positions.remove(choice);
			if (pos == 0) {
				// Check up
				if ((y + 1) < map.getHeight() && !map.getTile(x, y + 1).isOccupied()) {
					if (Math.abs(map.getTile(x, y + 1).getDirt() - map.getTile(x, y).getDirt()) > 2) {
						return null;
					} else {
						return new int[] { x, y + 1 };
					}
				}
			} else if (pos == 1) {
				// Check left
				if ((x - 1) >= 0 && !map.getTile(x - 1, y).isOccupied()) {
					if (Math.abs(map.getTile(x - 1, y).getDirt() - map.getTile(x, y).getDirt()) > 2) {
						return null;
					} else {
						return new int[] { x - 1, y };
					}
				}
			} else if (pos == 2) {
				// Check right
				if ((x + 1) < map.getWidth() && !map.getTile(x + 1, y).isOccupied()) {
					if (Math.abs(map.getTile(x + 1, y).getDirt() - map.getTile(x, y).getDirt()) > 2) {
						return null;
					} else {
						return new int[] { x + 1, y };
					}
				}
			} else if (pos == 3) {
				// Check down
				if ((y - 1) >= 0 && !map.getTile(x, y - 1).isOccupied()) {
					if (Math.abs(map.getTile(x, y - 1).getDirt() - map.getTile(x, y).getDirt()) > 2) {
						return null;
					} else {
						return new int[] { x, y - 1 };
					}
				}
			}
		}
		return null;
	}
	
	protected static int getRandomRange(int value, double range) {
		Random rnd = new Random();
		double chance = (95 + ((rnd.nextDouble() * range) * 10)) / 100;
		return (int) (value * chance);
	}
	
	protected static boolean move(Agent agent, int newX, int newY, Tile[][] map) {
		int x = agent.getX();
		int y = agent.getY();
		int heightDiff = Math.abs(map[x][y].getDirt() - map[newX][newY].getDirt());

		if (heightDiff > 1 && (agent.getDirt() > 0 || agent.getFood() > 0)) {
			if (agent.getHealth() > (2 * Agent.MOVE_HEALTH)) {
				swap(agent, newX, newY, map);
				agent.setHealth(agent.getHealth() - (2 * Agent.MOVE_HEALTH));
				return true;
			} else {
				return false;
			}
		} else {
			if(heightDiff > 1) {
				if (agent.getHealth() > Agent.MOVE_HEALTH) {
					swap(agent, newX, newY, map);
					agent.setHealth(agent.getHealth() - Agent.MOVE_HEALTH);
					return true;
				} else {
					return false;
				}
			}
			else {
				if(agent.getDirt() > 0 || agent.getFood() > 0) {
					if (agent.getHealth() > Agent.MOVE_HEALTH) {
						swap(agent, newX, newY, map);
						agent.setHealth(agent.getHealth() - Agent.MOVE_HEALTH);
						return true;
					} else {
						return false;
					}
				}
				else {
					swap(agent, newX, newY, map);
					return true;
				}
			}
		}
	}
	
	private static void swap(Agent agent, int newX, int newY, Tile[][] map) {
		map[newX][newY].setAgent(agent);
		map[agent.getX()][agent.getY()].setAgent(null);
		agent.setX(newX);
		agent.setY(newY);
		agent.addVisited(agent.getCurrentPos());
	}
}
