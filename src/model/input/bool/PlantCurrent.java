package model.input.bool;

import model.Agent;
import model.Map;
import model.input.DecisionBoolean;

public class PlantCurrent extends DecisionBoolean {

	@Override
	public boolean decide(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY();
		return hasPlant(x, y, map);
	}
	
	public String toString() {
		String output = Option.PLANT_CURRENT.toString();
		return output;
	}

}
