package model.output;

import model.Agent;
import model.Map;

public class MoveLeft extends Action {

	@Override
	public boolean action(Agent agent, Map map) {
		int newX = agent.getX() - 1;
		int newY = agent.getY();
		if (newX >= 0) {
			int dirt = map.getTile(agent.getX(), agent.getY()).getDirt();
			int newDirt = map.getTile(newX, newY).getDirt();
			if (Math.abs(dirt - newDirt) < 3) {
				if (!map.getTiles()[newX][newY].isOccupied()) {
					if (move(agent, newX, newY, map.getTiles())) {
						return true;
					} else {
						System.out.println("Cannot " + agent.getAction() + " because move would kill");
					}
				} else {
					System.out.println("Cannot " + agent.getAction() + " because of "
							+ map.getTiles()[newX][newY].getAgent().getID());
				}
			} else {
				System.out.println("Cannot " + agent.getAction() + " because of height difference");
			}
		} else {
			System.out.println("Cannot " + agent.getAction() + " because of out of bounds");
		}
		return false;
	}

	public String toString() {
		String output = getActivity().toString();
		return output;
	}
	
	@Override
	public Activity getActivity() {
		return Activity.MOVE_LEFT;
	}
}
