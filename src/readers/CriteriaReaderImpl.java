package readers;

import java.util.ArrayList;
import java.util.List;

import model.Player;
import model.Thing;
import model.XY;
import model.criteria.Annihilate;
import model.criteria.CollectFood;
import model.criteria.Criteria;
import model.criteria.Criteria.Condition;
import model.criteria.FindThing;
import model.criteria.LevelUp;
import model.criteria.MapDirt;
import model.criteria.PerformAction;
import model.criteria.SurviveTurns;
import model.criteria.TravelTo;

public class CriteriaReaderImpl implements CriteriaReader {

	private ActionReader actionReader;
	
	public CriteriaReaderImpl(ActionReader actionReader) {
		setActionReader(actionReader);
	}
	
	public ActionReader getActionReader() {
		return actionReader;
	}

	public void setActionReader(ActionReader actionReader) {
		this.actionReader = actionReader;
	}

	@Override
	public Criteria readCriteria(List<Thing> things, List<Player> players, String criteriaData) {
		String[] tokens = criteriaData.split(" ");
		Condition condition = Condition.valueOf(tokens[0]);
		switch(condition) {
		case SURVIVE_TURNS:
			return new SurviveTurns(Integer.valueOf(tokens[1]));
		case ANNIHILATE:
			return new Annihilate(findPlayer(tokens[1], players));
		case COLLECT_FOOD:
			int food = Integer.valueOf(tokens[2]);
			return new CollectFood(findPlayer(tokens[1], players), food);
		case LEVEL_UP:
			int exp = Integer.valueOf(tokens[2]);
			return new LevelUp(findPlayer(tokens[1], players), exp);
		case MAP_DIRT:
			int dirt = Integer.valueOf(tokens[1]);
			int x = Integer.valueOf(tokens[2]);
			int y = Integer.valueOf(tokens[3]);
			return new MapDirt(dirt, new XY(x, y));
		case TRAVEL_TO:
			x = Integer.valueOf(tokens[2]);
			y = Integer.valueOf(tokens[3]);
			return new TravelTo(findPlayer(tokens[1], players), new XY(x, y));
		case PERFORM_ACTION:
			int times = Integer.valueOf(tokens[3]);
			return new PerformAction(findPlayer(tokens[1], players), getActionReader().readActivity(tokens[2]), times);
		case FIND_THING:
			return new FindThing(findThing(tokens[1], things));
		default:
			return new SurviveTurns(5);
		}
	}

	@Override
	public List<Criteria> readCriteriaList(List<Thing> things, List<Player> players, String gameData) {
		List<Criteria> criteria = new ArrayList<Criteria>();
		String[] lines = gameData.split(System.lineSeparator());
		int criteriaLine = 0;
		int criteriaNumber = 0;
		for(int i = 0; i < lines.length; i++) {
			String[] values = lines[i].split("=");
			if(values[0].equals("criteria")) {
				criteriaLine = i;
				criteriaNumber = Integer.valueOf(values[1]);
			}
		}
		for(int i = criteriaLine + 1; i <= criteriaLine + criteriaNumber; i++) {
			criteria.add(readCriteria(things, players, lines[i]));
		}
		return criteria;
	}
	
	private Player findPlayer(String playerName, List<Player> players) {
		for(Player player : players) {
			if(player.getName().equals(playerName)) {
				return player;
			}
		}
		return null;
	}
	
	private Thing findThing(String thingID, List<Thing> things) {
		for(Thing thing : things) {
			if(thing.getID().equals(thingID)) {
				return thing;
			}
		}
		return null;
	}
}
