package model.output;

import model.Agent;
import model.Map;
import model.Player;
import model.tree.Tree;

public class Reproduce extends Action {

	@Override
	public boolean action(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY();
		int health = agent.getHealth();
		double change = 1.0 * health / agent.getMaxHealth();
		if (health < 2) {
			System.out.println("Cannot " + agent.getAction() + " not enough health");
			return false;
		} else {
			Player player = agent.getPlayer();
			if (player.hasSpace()) {
				int maxHealth = getRandomRange(agent.getMaxHealth(), change);
				int speed = getRandomRange(agent.getSpeed(), change);
				int power = getRandomRange(agent.getPower(), change);
				Tree tree = agent.getTree();
				int[] newPos = findPosition(map, x, y);
				if (newPos != null) {
					Agent newAgent = new Agent(newPos[0], newPos[1], player, speed, maxHealth, power, tree, map.getTime());
					newAgent.setHealth(maxHealth / 2);
					agent.setHealth(agent.getHealth() / 2);
					player.addAgent(newAgent);
					map.addAgent(newAgent);
					map.getTile(newPos[0], newPos[1]).setAgent(newAgent);
					return true;
				} else {
					System.out.println("Cannot " + agent.getAction() + " no extra locations");
					return false;
				}
			} else {
				System.out.println("Cannot " + agent.getAction() + " team full");
				return false;
			}
		}
	}
	
	public String toString() {
		String output = getActivity().toString();
		return output;
	}
	
	@Override
	public Activity getActivity() {
		return Activity.REPRODUCE;
	}

}
