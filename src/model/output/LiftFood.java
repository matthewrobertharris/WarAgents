package model.output;

import model.Agent;
import model.Map;

public class LiftFood extends Action {

	@Override
	public boolean action(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY();
		int food = map.getTile(x, y).getFood();
		if (food > 0) {
			if (agent.getDirt() == 0) {
				if (agent.getFood() < Agent.PICKUP_FOOD) {
					int freeFood = Agent.PICKUP_FOOD - agent.getFood();
					if (freeFood > food) {
						map.getTile(x, y).setFood(0);
						agent.setFood(food + agent.getFood());
					} else {
						map.getTile(x, y).setFood(food - freeFood);
						agent.setFood(Agent.PICKUP_FOOD);
					}
					return true;
				} else {
					System.out.println("Cannot " + agent.getAction() + " because agent already has maximum food");
				}
			} else {
				System.out.println("Cannot " + agent.getAction() + " because agent already has dirt");
			}
		} else {
			System.out.println("Cannot " + agent.getAction() + " because no food left on map");
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
