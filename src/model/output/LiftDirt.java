package model.output;

import model.Agent;
import model.Map;

public class LiftDirt extends Action {

	@Override
	public boolean action(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY();
		int dirt = map.getTile(x, y).getDirt();
		// if (height > 0) {
		if (agent.getDirt() == 0) {
			if (agent.getFood() == 0) {
				if (Agent.PICKUP_DIRT > dirt) {
					map.getTile(x, y).setDirt(0);
					agent.setDirt(dirt);
				} else {
					map.getTile(x, y).setDirt(dirt - Agent.PICKUP_DIRT);
					agent.setDirt(Agent.PICKUP_DIRT);
				}
				return true;
			} else {
				System.out.println("Cannot " + agent.getAction() + " because agent already has food");
			}
		} else {
			System.out.println("Cannot " + agent.getAction() + " because agent already has dirt");
		}
		// } else {
		// System.out.println("Cannot " + agent.getAction() + " because no dirt
		// left on map");
		// }
		return false;
	}
	
	public String toString() {
		String output = getActivity().toString();
		return output;
	}
	
	@Override
	public Activity getActivity() {
		return Activity.LIFT_DIRT;
	}

}
