package model.input.bool;

import model.Agent;
import model.Map;
import model.input.DecisionBoolean;

public class FoodAdjacent extends DecisionBoolean {

	@Override
	public boolean decide(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY();
		if (checkFood(x - 1, y, map) > 0) {
			return true;
		}
		if (checkFood(x + 1, y, map) > 0) {
			return true;
		}
		if (checkFood(x, y - 1, map) > 0) {
			return true;
		}
		if (checkFood(x, y + 1, map) > 0) {
			return true;
		}
		return false;
	}

	public String toString() {
		String output = Option.FOOD_ADJACENT.toString();
		return output;
	}
	
}
