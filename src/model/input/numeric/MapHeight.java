package model.input.numeric;

import model.Agent;
import model.Map;
import model.input.DecisionNumeric;

public class MapHeight extends DecisionNumeric {

	@Override
	public int decide(Agent agent, Map map) throws Exception {
		return map.getHeight();
	}
	
	public String toString() {
		String output = Option.MAP_HEIGHT.toString();
		return output;
	}

}
