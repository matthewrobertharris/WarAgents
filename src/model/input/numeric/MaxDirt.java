package model.input.numeric;

import model.Agent;
import model.Map;
import model.Tile;
import model.input.DecisionNumeric;

public class MaxDirt extends DecisionNumeric {

	@Override
	public int decide(Agent agent, Map map) throws Exception {
		return Tile.MAX_DIRT;
	}
	
	public String toString() {
		String output = Option.MAX_DIRT.toString();
		return output;
	}

}
