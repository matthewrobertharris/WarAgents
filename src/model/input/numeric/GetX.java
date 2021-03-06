package model.input.numeric;

import model.Agent;
import model.Map;
import model.XY;
import model.input.DecisionNumeric;
import model.input.GetPosition;

public class GetX extends DecisionNumeric {

	private GetPosition position;

	public GetX(GetPosition position) {
		setPosition(position);
	}

	public GetPosition getPosition() {
		return position;
	}

	public void setPosition(GetPosition position) {
		this.position = position;
	}

	@Override
	public int decide(Agent agent, Map map) throws Exception {
		XY position = getPosition().getPosition(agent, map);
		return position.getX();
	}
	
	public String toString() {
		String output = Option.GET_X.toString() + " " + getPosition().toString();
		return output;
	}

}
