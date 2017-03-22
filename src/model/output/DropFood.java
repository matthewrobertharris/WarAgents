package model.output;

import model.Agent;
import model.Map;

public class DropFood extends Action {

	@Override
	public boolean action(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY();
		int food = map.getTile(x, y).getFood();
		if (agent.getFood() > 0) {
			map.getTile(x, y).setFood(food + agent.getFood());
			agent.setFood(0);
			return true;
		} else {
			System.out.println("Cannot " + agent.getAction() + " because agent has no food");
			return false;
		}
	}

	public String toString() {
		String output = getActivity().toString();
		return output;
	}

	@Override
	public Activity getActivity() {
		return Activity.DROP_FOOD;
	}

}
