package model.input.bool;

import model.Agent;
import model.Map;
import model.XY;
import model.input.DecisionBoolean;
import model.input.GetPosition;

public class InBounds extends DecisionBoolean {

	private GetPosition position;

	public InBounds(GetPosition position) {
		setPosition(position);
	}

	public GetPosition getPosition() {
		return position;
	}

	public void setPosition(GetPosition position) {
		this.position = position;
	}

	@Override
	public boolean decide(Agent agent, Map map) throws Exception {
		XY position = getPosition().getPosition(agent, map);
		return inBounds(position, map);
	}
	
	public String toString() {
		String output = Option.IN_BOUNDS.toString() + " " + getPosition().toString();
		return output;
	}

}
