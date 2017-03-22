package model.criteria;

import model.Map;

public class SurviveTurns implements Criteria {

	private int turns;

	public SurviveTurns(int turns) {
		setTurns(turns);
	}

	public int getTurns() {
		return turns;
	}

	public void setTurns(int turns) {
		this.turns = turns;
	}

	@Override
	public boolean isFinished(Map map) {
		return (map.getTime() >= getTurns());
	}
	
	@Override
	public String toString() {
		String output = "SURVIVE_TURNS: Turns=" + getTurns();
		return output;
	}

}
