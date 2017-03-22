package model.output;

import model.Agent;
import model.Map;

public class LiftFood extends Action {

	
	public boolean action(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY();
		int food = map.getTile(x, y).getFood();
		if (food > 0) {
			if (agent.getDirt() == 0) {
				if (agent.getFood() == 0) {
					if (Agent.PICKUP_FOOD > food) {
						map.getTile(x, y).setFood(0);
						agent.setFood(food);
					} else {
						map.getTile(x, y).setFood(food - Agent.PICKUP_FOOD);
						agent.setFood(Agent.PICKUP_FOOD);
					}
					return true;
				} else {
					System.out.println("Cannot " + agent.getAction() + " because agent already has food");
				}
			} else {
				System.out.println("Cannot " + agent.getAction() + " because agent already has dirt");
			}
		} else {
			System.out.println("Cannot " + agent.getAction() + " because no dirt left on map");
		}
		return false;
	}
	
	public String toString() {
		String output = getActivity().toString();
		return output;
	}
	
	@Override
	public Activity getActivity() {
		return Activity.LIFT_FOOD;
	}
}
