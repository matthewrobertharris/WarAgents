package model.input;

import model.Agent;
import model.Map;
import model.XY;

public abstract class DecisionPosition extends Input {
	public abstract XY decide(Agent agent, Map map) throws Exception;
}
