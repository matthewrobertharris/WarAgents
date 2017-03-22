package model.input.numeric;

import model.Agent;
import model.Map;
import model.input.DecisionNumeric;

public class Time extends DecisionNumeric {

	@Override
	public int decide(Agent agent, Map map) throws Exception {
		return map.getTime();
	}

}
