package model.input.numeric;

import model.Agent;
import model.Map;
import model.Plant;
import model.Tile;
import model.XY;
import model.input.DecisionNumeric;
import model.input.GetPosition;

public class PlantRate extends DecisionNumeric {

	private GetPosition position;

	public PlantRate(GetPosition position) {
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
		Tile tile = map.getTile(position);
		Plant plant = tile.getPlant();
		return plant.getRate();
	}
	
	public String toString() {
		String output = Option.PLANT_RATE.toString();
		return output;
	}

}
