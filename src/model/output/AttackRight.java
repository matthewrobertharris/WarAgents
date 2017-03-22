package model.output;

import model.Agent;
import model.Map;

public class AttackRight extends Action {

	@Override
	public boolean action(Agent agent, Map map) {
		int newX = agent.getX() + 1;
		int newY = agent.getY();
		if (newX < (map.getWidth())) {
			if (map.getTile(newX, newY).isOccupied()) {
				if (attack(agent, map.getTile(newX, newY).getAgent(), map)) {
					return true;
				} else {
					System.out.println("Cannot " + agent.getAction() + " because attack failed");
				}
			} else {
				System.out.println("Cannot " + agent.getAction() + " because no agent to attack");
			}
		} else {
			System.out.println("Cannot " + agent.getAction() + " because attack is out of bounds");
		}
		return false;
	}

	@Override
	public Activity getActivity() {
		return Activity.ATTACK_RIGHT;
	}

	public String toString() {
		String output = getActivity().toString();
		return output;
	}
	
}
