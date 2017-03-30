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

		if (agent.getFood() == 0) {
			if (dirt > 0) {
				if (agent.getDirt() < Agent.PICKUP_DIRT) {
					int freeDirt = Agent.PICKUP_DIRT - agent.getDirt();
					if (freeDirt > dirt) {
						map.getTile(x, y).setDirt(0);
						agent.setDirt(dirt + agent.getDirt());
					} else {
						map.getTile(x, y).setDirt(dirt - freeDirt);
						agent.setDirt(Agent.PICKUP_DIRT);
					}
					return true;
				} else {
					System.out.println("Cannot " + agent.getAction() + " because agent already has maximum dirt");
				}
			} else {
				System.out.println("Cannot " + agent.getAction() + " because there is no dirt");
			}
		} else {
			System.out.println("Cannot " + agent.getAction() + " because agent already has food");
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
