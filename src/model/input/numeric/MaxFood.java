package model.input.numeric;

import model.Agent;
import model.Map;
import model.Tile;
import model.input.DecisionNumeric;

public class MaxFood extends DecisionNumeric {

	@Override
	public int decide(Agent agent, Map map) throws Exception {
		return Tile.MAX_FOOD;
	}
	
	public String toString() {
		String output = Option.MAX_FOOD.toString();
		return output;
	}

}
