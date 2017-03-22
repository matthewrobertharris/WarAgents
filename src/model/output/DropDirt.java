package model.output;

import model.Agent;
import model.Map;

public class DropDirt extends Action {

	@Override
	public boolean action(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY();
		int height = map.getTile(x, y).getDirt();
		if (agent.getDirt() > 0) {
			map.getTile(x, y).setDirt(height + agent.getDirt());
			agent.setDirt(0);
			return true;
		} else {
			System.out.println("Cannot " + agent.getAction() + " because agent has no dirt");
			return false;
		}
	}
	
	@Override
	public Activity getActivity() {
		return Activity.DROP_DIRT;
	}

	public String toString() {
		String output = getActivity().toString();
		return output;
	}
	
}
