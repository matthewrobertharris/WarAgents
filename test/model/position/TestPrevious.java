package model.position;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import org.junit.After;
import org.junit.Test;

import junit.framework.TestCase;
import main.Game;
import model.Agent;
import model.Map;
import model.XY;
import model.input.DecisionPosition;
import model.input.position.DirectionTo;
import model.output.Action.Activity;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class TestPrevious extends TestCase {

	private GameReader gameReader;
	private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();

	@Override
	protected void setUp() {
		gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		System.setOut(new PrintStream(outContent));
	}
	
	@After
	public void cleanUpStreams() {
	    System.setOut(null);
	}

	@Test
	public void testPrevious_Success() {
		String file = "resources\\test\\positionMaps\\test_previous_success.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		XY previous = new XY(1, 2);
		agent.getVisited().add(0, previous);

		DecisionPosition decision = (DecisionPosition)agent.getTree().getRoot().getInputs().get(0);
		DirectionTo directionTo = (DirectionTo)decision;
		XY position = directionTo.getPosition().getPosition(agent, map);
		
		assertTrue(position.getX() == 1);
		assertTrue(position.getY() == 2);
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.MOVE_LEFT);
		assertTrue(map.getAllAgents().size() == 1);
	}
	
	@Test
	public void testPrevious_Fail_NotSet() {
		String file = "resources\\test\\positionMaps\\test_previous_fail_noPrevious.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);

		DecisionPosition decision = (DecisionPosition)agent.getTree().getRoot().getInputs().get(0);
		DirectionTo directionTo = (DirectionTo)decision;
		XY position = directionTo.getPosition().getPosition(agent, map);
		
		assertTrue(position == null);
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.CONFUSED);
		assertTrue(map.getAllAgents().size() == 1);
	}
	
	@Test
	public void test_ToString() {
		Previous position = new Previous();
		String output = "PREVIOUS";
		assertTrue(position.toString().equals(output));
	}
}
