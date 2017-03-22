package model.input.bool;

import model.Agent;
import model.Map;
import model.input.DecisionBoolean;

public class PlantAdjacent extends DecisionBoolean {

	@Override
	public boolean decide(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY();
		if(hasPlant(x, y, map)) {
			return true;
		}
		if (hasPlant(x - 1, y, map)) {
			return true;
		}
		if (hasPlant(x + 1, y, map)) {
			return true;
		}
		if (hasPlant(x, y - 1, map)) {
			return true;
		}
		if (hasPlant(x, y + 1, map)) {
			return true;
		}
		return false;
	}
	
	public String toString() {
		String output = Option.PLANT_ADJACENT.toString();
		return output;
	}

}
