package model.input;

import model.Agent;
import model.Map;

public abstract class DecisionNumeric extends Input {

	public abstract int decide(Agent agent, Map map) throws Exception;
	
}
