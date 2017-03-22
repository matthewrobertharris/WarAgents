package model.output;

import model.Agent;
import model.Map;

public class Eat extends Action {

	@Override
	public boolean action(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY();
		int food = map.getTile(x, y).getFood();
		int health = agent.getHealth();
		int maxHealth = agent.getMaxHealth();
		if (health == maxHealth) {
			System.out.println("Cannot " + agent.getAction() + " because agent is at full health");
			return false;
		} else {
			if (food == 0) {
				System.out.println("Cannot " + agent.getAction() + " because map has no food");
				return false;
			} else {
				if (maxHealth - health > food) {
					map.getTile(x, y).setFood(0);
					agent.setHealth(health + food);
					return true;
				} else {
					map.getTile(x, y).setFood(food - (maxHealth - health));
					agent.setHealth(maxHealth);
					return true;
				}
			}
		}
	}
	
	public String toString() {
		String output = getActivity().toString();
		return output;
	}
	
	@Override
	public Activity getActivity() {
		return Activity.EAT;
	}

}
