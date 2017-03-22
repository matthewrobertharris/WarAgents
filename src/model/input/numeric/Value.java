package model.input.numeric;

import model.Agent;
import model.Map;
import model.input.DecisionNumeric;

public class Value extends DecisionNumeric {

	private int value;
	
	public Value(int value) {
		setValue(value);
	}
	
	public int getValue() {
		return value;
	}

	public void setValue(int value) {
		this.value = value;
	}

	@Override
	public int decide(Agent agent, Map map) {
		return getValue();
	}
	
	public String toString() {
		String output = Option.VALUE.toString() + "=" + getValue();
		return output;
	}

}
