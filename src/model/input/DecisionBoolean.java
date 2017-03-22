package model.input;

import model.Agent;
import model.Map;

public abstract class DecisionBoolean extends Input {

	public abstract boolean decide(Agent agent, Map map) throws Exception;
}
