package model.input.numeric;

import model.Agent;
import model.Map;
import model.input.DecisionNumeric;

public class MapWidth extends DecisionNumeric {

	@Override
	public int decide(Agent agent, Map map) throws Exception {
		return map.getWidth();
	}
	
	public String toString() {
		String output = Option.MAP_WIDTH.toString();
		return output;
	}

}
